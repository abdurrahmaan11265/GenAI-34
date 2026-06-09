"""
Ingestion Orchestrator — Batched & Checkpointed.

Pipeline stages are fully resumable. A crash at any point is safe to retry:
  1. PARSING     — Fetch job metadata.
  2. CHUNKING    — Persist chunks in batches of CHUNK_BATCH. Idempotent on conflict.
  3. EXTRACTING_CONCEPTS     — Per-chunk LLM call, persist raw_concepts. Skip chunks
                               that already have a raw_concept row. Batch commit every
                               RAW_CONCEPT_BATCH chunks.
  4. CANONICALIZING          — Load all raw_concepts, cluster + merge, write canonical
                               concepts. Single commit (fast, no LLM).
  5. EXTRACTING_RELATIONSHIPS — Generate candidate pairs once, write to
                               relationship_candidates. Then iterate PENDING candidates,
                               call LLM, write to evaluated_pairs + concept_edges.
                               Commit every REL_BATCH pairs.
  6. VALIDATING  — Graph validator.
  7. REPAIRING   — Cycle repair.
  8. PUBLISHING  — Mark graph_versions.is_current = TRUE, book.status = 'KG_BUILT'.
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.canonicalization import CanonicalizationEngine
from app.services.chunking import Chunker
from app.services.document_parser import DocumentParser
from app.services.graph_builder import CandidatePairGenerator
from app.services.graph_repair import GraphRepair
from app.services.graph_validator import GraphValidator
from app.services.llm_extractor import LLMExtractor
from app.services.storage import StorageProvider

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Tunable batch sizes
# ──────────────────────────────────────────────
CHUNK_BATCH = 20        # commit every N chunks written
RAW_CONCEPT_BATCH = 20  # commit every N chunk extractions
REL_BATCH = 50          # commit every N relationship candidates processed


class IngestionOrchestrator:
    def __init__(self, storage_provider: StorageProvider):
        self.storage = storage_provider
        self.chunker = Chunker()
        self.llm = LLMExtractor()
        self.canon = CanonicalizationEngine()

    # ──────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────
    async def process_job(self, job_id: str, db: AsyncSession) -> bool:
        try:
            ctx = await self._fetch_job_context(job_id, db)
            book_id = ctx["book_id"]
            storage_path = ctx["storage_path"]
            graph_version_num = ctx["graph_version"]
            version_id = await self._ensure_graph_version(book_id, graph_version_num, job_id, db)

            # ── CHUNKING ────────────────────────────────────────────────────
            await self._set_stage(job_id, "CHUNKING", db)
            chunk_ids = await self._stage_chunking(book_id, storage_path, db)

            # ── EXTRACTING_CONCEPTS ─────────────────────────────────────────
            await self._set_stage(job_id, "EXTRACTING_CONCEPTS", db)
            await self._stage_raw_concepts(book_id, version_id, chunk_ids, db)

            # ── CANONICALIZING ──────────────────────────────────────────────
            await self._set_stage(job_id, "CANONICALIZING", db)
            canonical_concepts = await self._stage_canonicalize(book_id, graph_version_num, version_id, db)

            # ── EXTRACTING_RELATIONSHIPS ────────────────────────────────────
            await self._set_stage(job_id, "EXTRACTING_RELATIONSHIPS", db)
            edges = await self._stage_relationships(book_id, graph_version_num, version_id, canonical_concepts, db)

            # ── VALIDATING ──────────────────────────────────────────────────
            await self._set_stage(job_id, "VALIDATING", db)
            failures = GraphValidator.validate(canonical_concepts, edges)
            for f in failures:
                await db.execute(
                    text("""
                        INSERT INTO graph_validation_results
                            (graph_version_id, rule_code, passed, severity, detail)
                        VALUES (:vid, :rc, :pass, :sev, :det)
                        ON CONFLICT DO NOTHING
                    """),
                    {"vid": version_id, "rc": f["rule"], "pass": f["passed"],
                     "sev": f["severity"], "det": json.dumps(f["detail"])},
                )

            # ── REPAIRING ───────────────────────────────────────────────────
            await self._set_stage(job_id, "REPAIRING", db)
            cycle_failures = [f["detail"]["cycles"] for f in failures if f["rule"] == "V01" and not f["passed"]]
            if cycle_failures:
                edges_to_remove = GraphRepair.repair_cycles(cycle_failures[0], edges)
                for edge in edges_to_remove:
                    await db.execute(text("DELETE FROM concept_edges WHERE id = :id"), {"id": edge["id"]})
                    edges.remove(edge)
                    await db.execute(
                        text("""
                            INSERT INTO graph_repair_log
                                (graph_version_id, operation, artifact_id, reason, before_value)
                            VALUES (:vid, 'DELETE_EDGE', :eid, 'CYCLE_REPAIR', :val)
                        """),
                        {"vid": version_id, "eid": edge["id"], "val": json.dumps(edge)},
                    )

            # ── PUBLISHING ──────────────────────────────────────────────────
            await self._set_stage(job_id, "PUBLISHING", db)
            await db.execute(
                text("UPDATE books SET status = 'KG_BUILT' WHERE id = :bid"),
                {"bid": book_id},
            )
            await db.execute(
                text("""
                    UPDATE graph_build_jobs
                    SET status = 'COMPLETED', completed_at = NOW(),
                        current_stage = 'COMPLETED',
                        nodes_created = :nodes, edges_created = :edges
                    WHERE id = :job_id
                """),
                {"nodes": len(canonical_concepts), "edges": len(edges), "job_id": job_id},
            )

            # Clean up source file if configured
            if not settings.KEEP_SOURCE_FILE:
                try:
                    self.storage.delete(storage_path)
                    await db.execute(
                        text("UPDATE book_uploads SET upload_status = 'STORED' WHERE storage_path = :p"),
                        {"p": storage_path},
                    )
                except Exception as del_err:
                    logger.warning(f"Could not delete source file {storage_path}: {del_err}")

            await db.commit()
            logger.info(f"Job {job_id} completed — {len(canonical_concepts)} nodes, {len(edges)} edges")
            return True

        except Exception as exc:
            await db.rollback()
            err_msg = str(exc)
            logger.error(f"Job {job_id} failed: {err_msg}", exc_info=True)
            try:
                await db.execute(
                    text("""
                        UPDATE graph_build_jobs
                        SET status = 'FAILED', error_message = :err,
                            last_error = :err, completed_at = NOW()
                        WHERE id = :job_id
                    """),
                    {"err": err_msg, "job_id": job_id},
                )
                await db.commit()
            except Exception:
                pass
            return False

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────
    async def _fetch_job_context(self, job_id: str, db: AsyncSession) -> Dict[str, Any]:
        result = await db.execute(
            text("""
                SELECT g.book_id, u.storage_path, g.graph_version
                FROM graph_build_jobs g
                JOIN book_uploads u ON g.book_upload_id = u.id
                WHERE g.id = :job_id
            """),
            {"job_id": job_id},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Job {job_id} not found or missing book_upload.")
        return {"book_id": row[0], "storage_path": row[1], "graph_version": row[2]}

    async def _set_stage(self, job_id: str, stage: str, db: AsyncSession, offset: int = 0) -> None:
        logger.info(f"Job {job_id} → stage {stage}")
        await db.execute(
            text("""
                UPDATE graph_build_jobs
                SET status = :stage, current_stage = :stage, current_offset = :offset, updated_at = NOW()
                WHERE id = :job_id
            """),
            {"stage": stage, "offset": offset, "job_id": job_id},
        )
        await db.commit()

    async def _ensure_graph_version(
        self, book_id: str, graph_version_num: int, job_id: str, db: AsyncSession
    ) -> str:
        vid = str(uuid.uuid4())
        result = await db.execute(
            text("""
                INSERT INTO graph_versions (id, book_id, version, is_current, build_job_id)
                VALUES (:id, :book_id, :v, FALSE, :job_id)
                ON CONFLICT (book_id, version) DO NOTHING
                RETURNING id
            """),
            {"id": vid, "book_id": book_id, "v": graph_version_num, "job_id": job_id},
        )
        row = result.fetchone()
        if row:
            await db.commit()
            return str(row[0])
        existing = await db.execute(
            text("SELECT id FROM graph_versions WHERE book_id = :bid AND version = :v"),
            {"bid": book_id, "v": graph_version_num},
        )
        return str(existing.fetchone()[0])

    # ──────────────────────────────────────────────
    # Stage 2: Chunking
    # ──────────────────────────────────────────────
    async def _stage_chunking(self, book_id: str, storage_path: str, db: AsyncSession) -> List[Dict]:
        logger.info(f"Parsing document at {storage_path}")
        parsed_doc = DocumentParser.parse(storage_path)
        logger.info("Chunking document")
        chunks = self.chunker.chunk_document(parsed_doc)

        chunk_records: List[Dict] = []
        pending_batch: List[Dict] = []

        for chunk in chunks:
            cid = str(uuid.uuid4())
            pending_batch.append({
                "id": cid, "book_id": book_id,
                "idx": chunk["chunk_index"], "content": chunk["content"],
                "tokens": chunk["token_count"], "ps": chunk["page_start"], "pe": chunk["page_end"],
            })

            if len(pending_batch) >= CHUNK_BATCH:
                chunk_records.extend(await self._flush_chunks(pending_batch, book_id, db))
                pending_batch = []

        if pending_batch:
            chunk_records.extend(await self._flush_chunks(pending_batch, book_id, db))

        logger.info(f"Chunked into {len(chunk_records)} segments")
        return chunk_records

    async def _flush_chunks(self, batch: List[Dict], book_id: str, db: AsyncSession) -> List[Dict]:
        records = []
        for c in batch:
            result = await db.execute(
                text("""
                    INSERT INTO source_chunks
                        (id, book_id, chunk_index, content, token_count, page_start, page_end)
                    VALUES (:id, :book_id, :idx, :content, :tokens, :ps, :pe)
                    ON CONFLICT (book_id, chunk_index) DO NOTHING
                    RETURNING id
                """),
                c,
            )
            row = result.fetchone()
            if row:
                records.append({"db_id": str(row[0]), "content": c["content"]})
            else:
                existing = await db.execute(
                    text("SELECT id, content FROM source_chunks WHERE book_id = :bid AND chunk_index = :idx"),
                    {"bid": book_id, "idx": c["idx"]},
                )
                ex_row = existing.fetchone()
                if ex_row:
                    records.append({"db_id": str(ex_row[0]), "content": ex_row[1]})
        await db.commit()
        return records

    # ──────────────────────────────────────────────
    # Stage 3: Raw Concept Extraction
    # ──────────────────────────────────────────────
    async def _stage_raw_concepts(
        self, book_id: str, version_id: str, chunk_records: List[Dict], db: AsyncSession
    ) -> None:
        # Find which chunk_ids already have raw_concepts for this version_id
        existing_result = await db.execute(
            text("SELECT DISTINCT source_chunk_id FROM raw_concepts WHERE graph_version_id = :vid"),
            {"vid": version_id},
        )
        already_done: set = {str(r[0]) for r in existing_result.fetchall()}
        pending = [c for c in chunk_records if c["db_id"] not in already_done]

        logger.info(f"Extracting concepts: {len(pending)} chunks pending (skipping {len(already_done)} already done)")

        batch_count = 0
        for chunk in pending:
            extraction = self.llm.extract_concepts(chunk["content"])
            for concept in extraction.concepts:
                await db.execute(
                    text("""
                        INSERT INTO raw_concepts
                            (id, graph_version_id, source_chunk_id, name, summary, difficulty_level, subtopics)
                        VALUES (:id, :vid, :cid, :name, :sum, :diff, :subs)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()), "vid": version_id, "cid": chunk["db_id"],
                        "name": concept.name, "sum": concept.summary,
                        "diff": concept.difficulty,
                        "subs": json.dumps(list(getattr(concept, "subtopics", []) or [])),
                    },
                )
            batch_count += 1
            if batch_count % RAW_CONCEPT_BATCH == 0:
                await db.commit()
                logger.info(f"  … committed {batch_count}/{len(pending)} concept extractions")

        await db.commit()
        logger.info("Raw concept extraction complete")

    # ──────────────────────────────────────────────
    # Stage 4: Canonicalization
    # ──────────────────────────────────────────────
    async def _stage_canonicalize(
        self, book_id: str, graph_version_num: int, version_id: str, db: AsyncSession
    ) -> List[Dict]:
        # Check if canonical concepts already exist (resume case)
        existing_result = await db.execute(
            text("SELECT id, name, summary, difficulty_level, metadata FROM concepts WHERE book_id = :bid AND graph_version = :v"),
            {"bid": book_id, "v": graph_version_num},
        )
        existing_rows = existing_result.fetchall()
        if existing_rows:
            logger.info(f"Canonicalization skipped — {len(existing_rows)} concepts already exist")
            return [
                {
                    "id": str(r[0]), "canonical_name": r[1], "canonical_summary": r[2],
                    "difficulty": r[3],
                    "subtopics": (json.loads(r[4]) if r[4] else {}).get("subtopics", []),
                    "source_chunk_id": None,
                }
                for r in existing_rows
            ]

        # Load all raw concepts for this version
        raw_result = await db.execute(
            text("SELECT id, source_chunk_id, name, summary, difficulty_level, subtopics FROM raw_concepts WHERE graph_version_id = :vid"),
            {"vid": version_id},
        )
        raw_rows = raw_result.fetchall()
        raw_concepts = [
            {
                "name": r[2], "summary": r[3], "difficulty": r[4],
                "subtopics": json.loads(r[5]) if r[5] else [],
                "source_chunk_id": str(r[1]),
            }
            for r in raw_rows
        ]

        logger.info(f"Canonicalizing {len(raw_concepts)} raw concepts")
        clusters = self.canon.group_candidates(raw_concepts)
        canonical_concepts: List[Dict] = []

        for cluster in clusters:
            if len(cluster) == 1:
                resolved = cluster[0]
                resolved["canonical_name"] = resolved["name"]
                resolved["canonical_summary"] = resolved["summary"]
            else:
                merged = self.llm.resolve_merge(cluster)
                # Union subtopics from all candidates
                merged_subtopics: List[str] = []
                for cand in cluster:
                    for st in cand.get("subtopics", []):
                        if st not in merged_subtopics:
                            merged_subtopics.append(st)
                resolved = {
                    "canonical_name": merged.canonical_name,
                    "canonical_summary": merged.canonical_summary,
                    "difficulty": merged.difficulty,
                    "subtopics": merged_subtopics[:5],
                    "source_chunk_id": cluster[0]["source_chunk_id"],
                }

            concept_id = str(uuid.uuid4())
            resolved["id"] = concept_id
            metadata_json = json.dumps({"subtopics": resolved.get("subtopics", [])})

            result = await db.execute(
                text("""
                    INSERT INTO concepts (id, book_id, name, summary, difficulty_level, graph_version, metadata)
                    VALUES (:id, :book_id, :name, :sum, :diff, :v, :meta)
                    ON CONFLICT (book_id, name, graph_version) DO NOTHING
                    RETURNING id
                """),
                {
                    "id": concept_id, "book_id": book_id,
                    "name": resolved["canonical_name"], "sum": resolved["canonical_summary"],
                    "diff": resolved["difficulty"], "v": graph_version_num,
                    "meta": metadata_json,
                },
            )
            row = result.fetchone()
            if not row:
                existing = await db.execute(
                    text("SELECT id FROM concepts WHERE book_id = :bid AND name = :name AND graph_version = :v"),
                    {"bid": book_id, "name": resolved["canonical_name"], "v": graph_version_num},
                )
                ex_row = existing.fetchone()
                if ex_row:
                    resolved["id"] = str(ex_row[0])
            canonical_concepts.append(resolved)

            # Preserve lineage: link the canonical concept back to all source chunks that formed it
            source_chunk_ids = {c.get("source_chunk_id") for c in cluster if c.get("source_chunk_id")}
            for chunk_id in source_chunk_ids:
                await db.execute(
                    text("""
                        INSERT INTO concept_chunks (id, concept_id, chunk_id, relevance_score)
                        VALUES (:id, :concept_id, :chunk_id, 1.0)
                        ON CONFLICT DO NOTHING
                    """),
                    {"id": str(uuid.uuid4()), "concept_id": resolved["id"], "chunk_id": str(chunk_id)},
                )
            
            # Update raw_concepts lineage
            raw_concept_ids = [c["id"] for c in cluster]
            if raw_concept_ids:
                await db.execute(
                    text("""
                        UPDATE raw_concepts 
                        SET canonical_concept_id = :can_id, canonicalized_at = :now
                        WHERE id = ANY(:raw_ids)
                    """),
                    {
                        "can_id": resolved["id"],
                        "now": datetime.utcnow(),
                        "raw_ids": raw_concept_ids
                    }
                )

        await db.commit()
        logger.info(f"Canonicalization done — {len(canonical_concepts)} canonical concepts")
        return canonical_concepts

    # ──────────────────────────────────────────────
    # Stage 5: Relationship Extraction
    # ──────────────────────────────────────────────
    async def _stage_relationships(
        self,
        book_id: str,
        graph_version_num: int,
        version_id: str,
        canonical_concepts: List[Dict],
        db: AsyncSession,
    ) -> List[Dict]:
        # Ensure all candidate pairs exist in relationship_candidates table.
        # If they already exist we skip generation (resume).
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM relationship_candidates WHERE graph_version_id = :vid"),
            {"vid": version_id},
        )
        cand_count = count_result.scalar()

        if cand_count == 0:
            logger.info("Generating candidate pairs…")
            pairs = CandidatePairGenerator.generate_pairs(canonical_concepts)
            logger.info(f"Inserting {len(pairs)} candidate pairs into relationship_candidates")
            for src_id, tgt_id in pairs:
                await db.execute(
                    text("""
                        INSERT INTO relationship_candidates
                            (id, graph_version_id, source_concept_id, target_concept_id, status)
                        VALUES (:id, :vid, :src, :tgt, 'PENDING')
                        ON CONFLICT DO NOTHING
                    """),
                    {"id": str(uuid.uuid4()), "vid": version_id, "src": src_id, "tgt": tgt_id},
                )
            await db.commit()
            logger.info("Candidate pairs committed")
        else:
            logger.info(f"Resuming — {cand_count} candidate pairs already exist")

        # Build concept lookup
        by_id = {c["id"]: c for c in canonical_concepts}

        # Fetch PENDING candidates
        pending_result = await db.execute(
            text("""
                SELECT id, source_concept_id, target_concept_id
                FROM relationship_candidates
                WHERE graph_version_id = :vid AND status = 'PENDING'
                ORDER BY id
            """),
            {"vid": version_id},
        )
        pending = pending_result.fetchall()
        logger.info(f"Processing {len(pending)} PENDING relationship candidates")

        edges: List[Dict] = []
        # Pre-load already-accepted edges (from a partial run)
        done_edges_result = await db.execute(
            text("SELECT id, from_concept_id, to_concept_id, edge_type, confidence FROM concept_edges WHERE book_id = :bid AND graph_version = :v"),
            {"bid": book_id, "v": graph_version_num},
        )
        for row in done_edges_result.fetchall():
            edges.append({
                "id": str(row[0]), "source_concept_id": str(row[1]),
                "target_concept_id": str(row[2]),
                "relationship_type": row[3], "confidence": float(row[4]),
            })

        for i, (cand_id, src_id, tgt_id) in enumerate(pending):
            src_id = str(src_id)
            tgt_id = str(tgt_id)
            src_c = by_id.get(src_id)
            tgt_c = by_id.get(tgt_id)
            if not src_c or not tgt_c:
                await db.execute(
                    text("UPDATE relationship_candidates SET status = 'SKIPPED', processed_at = NOW() WHERE id = :id"),
                    {"id": str(cand_id)},
                )
                continue

            # Fetch chunk content for context
            chunk_content = ""
            if src_c.get("source_chunk_id"):
                res = await db.execute(
                    text("SELECT content FROM source_chunks WHERE id = :cid"),
                    {"cid": src_c["source_chunk_id"]},
                )
                row = res.fetchone()
                if row:
                    chunk_content = row[0]

            rel = self.llm.extract_relationship(chunk_content, src_c, tgt_c)
            status = "NO_RELATIONSHIP"
            confidence = float(rel.confidence)

            keep_edge = (
                (rel.relationship_type == "PREREQUISITE" and rel.confidence > 0.5)
                or (rel.relationship_type == "RELATED" and rel.confidence >= 0.85)
            )
            if keep_edge:
                edge_id = str(uuid.uuid4())
                await db.execute(
                    text("""
                        INSERT INTO concept_edges
                            (id, book_id, graph_version, from_concept_id, to_concept_id, edge_type, confidence)
                        VALUES (:id, :book_id, :v, :src, :tgt, :type, :conf)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": edge_id, "book_id": book_id, "v": graph_version_num,
                        "src": src_id, "tgt": tgt_id,
                        "type": rel.relationship_type, "conf": rel.confidence,
                    },
                )
                edges.append({
                    "id": edge_id, "source_concept_id": src_id, "target_concept_id": tgt_id,
                    "relationship_type": rel.relationship_type, "confidence": confidence,
                })
                status = "EDGE_CREATED"

            # Record in evaluated_pairs (graph-model-clean cache)
            await db.execute(
                text("""
                    INSERT INTO evaluated_pairs
                        (id, graph_version_id, source_concept_id, target_concept_id, status, confidence, llm_version)
                    VALUES (:id, :vid, :src, :tgt, :status, :conf, :llm)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()), "vid": version_id, "src": src_id, "tgt": tgt_id,
                    "status": status, "conf": confidence,
                    "llm": getattr(settings, "GEMINI_MODEL", "unknown"),
                },
            )
            # Mark candidate processed
            await db.execute(
                text("UPDATE relationship_candidates SET status = :s, confidence = :c, processed_at = NOW() WHERE id = :id"),
                {"s": status, "c": confidence, "id": str(cand_id)},
            )

            # Batch commit
            if (i + 1) % REL_BATCH == 0:
                await db.commit()
                logger.info(f"  … committed {i + 1}/{len(pending)} relationship evaluations")

        await db.commit()
        logger.info(f"Relationship extraction done — {len(edges)} edges accepted")
        return edges
