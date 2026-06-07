import logging
import uuid
import json
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.services.storage import StorageProvider
from app.services.document_parser import DocumentParser
from app.services.chunking import Chunker
from app.services.llm_extractor import LLMExtractor
from app.services.canonicalization import CanonicalizationEngine
from app.services.graph_builder import CandidatePairGenerator
from app.services.graph_validator import GraphValidator
from app.services.graph_repair import GraphRepair

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    def __init__(self, storage_provider: StorageProvider):
        self.storage_provider = storage_provider
        self.chunker = Chunker()
        self.llm_extractor = LLMExtractor()
        self.canonicalization = CanonicalizationEngine()
        
    async def process_job(self, job_id: str, db: AsyncSession) -> bool:
        try:
            logger.info(f"Starting ingestion job {job_id}")
            
            # Fetch job and upload info
            job_stmt = text('''
                SELECT g.book_id, u.storage_path, g.graph_version 
                FROM graph_build_jobs g
                JOIN book_uploads u ON g.book_upload_id = u.id
                WHERE g.id = :job_id
            ''')
            result = await db.execute(job_stmt, {"job_id": job_id})
            row = result.fetchone()
            if not row:
                raise ValueError(f"Job {job_id} not found or missing book_upload.")
            
            book_id, storage_path, graph_version_num = row
            
            # Stage 1: Parse
            logger.info(f"Parsing document at {storage_path}")
            parsed_doc = DocumentParser.parse(storage_path)
            
            # Stage 2: Chunk
            logger.info("Chunking document")
            chunks = self.chunker.chunk_document(parsed_doc)
            
            chunk_ids = []
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                stmt = text('''
                    INSERT INTO source_chunks (id, book_id, chunk_index, content, token_count, page_start, page_end)
                    VALUES (:id, :book_id, :idx, :content, :tokens, :ps, :pe)
                    ON CONFLICT (book_id, chunk_index) DO NOTHING
                    RETURNING id
                ''')
                result = await db.execute(stmt, {
                    "id": chunk_id, "book_id": book_id, "idx": chunk["chunk_index"],
                    "content": chunk["content"], "tokens": chunk["token_count"],
                    "ps": chunk["page_start"], "pe": chunk["page_end"]
                })
                returned = result.fetchone()
                if returned:
                    chunk["db_id"] = chunk_id
                else:
                    # Chunk already exists — get its real id
                    existing = await db.execute(
                        text('SELECT id FROM source_chunks WHERE book_id = :bid AND chunk_index = :idx'),
                        {"bid": book_id, "idx": chunk["chunk_index"]}
                    )
                    existing_row = existing.fetchone()
                    chunk["db_id"] = str(existing_row[0]) if existing_row else chunk_id
                chunk_ids.append(chunk["db_id"])
            
            # Stage 3: Extract Concepts
            logger.info("Extracting concepts")
            raw_concepts = []
            for chunk in chunks:
                extraction = self.llm_extractor.extract_concepts(chunk["content"])
                for c in extraction.concepts:
                    raw_concepts.append({
                        "name": c.name,
                        "summary": c.summary,
                        "difficulty": c.difficulty,
                        "subtopics": list(getattr(c, "subtopics", []) or []),
                        "source_chunk_id": chunk["db_id"]
                    })
            
            # Stage 4: Canonicalize
            logger.info("Canonicalizing concepts")
            clusters = self.canonicalization.group_candidates(raw_concepts)
            canonical_concepts = []
            
            # Create a graph version first (idempotent on retry)
            version_id = str(uuid.uuid4())
            result = await db.execute(text('''
                INSERT INTO graph_versions (id, book_id, version, is_current, build_job_id)
                VALUES (:id, :book_id, :v, FALSE, :job_id)
                ON CONFLICT (book_id, version) DO NOTHING
                RETURNING id
            '''), {"id": version_id, "book_id": book_id, "v": graph_version_num, "job_id": job_id})
            returned = result.fetchone()
            if not returned:
                # Version already exists, fetch its id
                existing = await db.execute(
                    text('SELECT id FROM graph_versions WHERE book_id = :bid AND version = :v'),
                    {"bid": book_id, "v": graph_version_num}
                )
                existing_row = existing.fetchone()
                if existing_row:
                    version_id = str(existing_row[0])
            
            for cluster in clusters:
                if len(cluster) == 1:
                    resolved = cluster[0]
                    resolved["canonical_name"] = resolved["name"]
                    resolved["canonical_summary"] = resolved["summary"]
                    resolved["subtopics"] = list(resolved.get("subtopics", []))
                else:
                    merged = self.llm_extractor.resolve_merge(cluster)
                    # Union the candidates' sub-topics (resolve_merge doesn't return them).
                    merged_subtopics = []
                    for cand in cluster:
                        for st in cand.get("subtopics", []):
                            if st not in merged_subtopics:
                                merged_subtopics.append(st)
                    resolved = {
                        "canonical_name": merged.canonical_name,
                        "canonical_summary": merged.canonical_summary,
                        "difficulty": merged.difficulty,
                        "subtopics": merged_subtopics[:5],
                        "source_chunk_id": cluster[0]["source_chunk_id"] # arbitrarily link to first chunk
                    }

                concept_id = str(uuid.uuid4())
                resolved["id"] = concept_id

                # Store sub-topics in metadata so the course/daily-plan can show them.
                metadata_json = json.dumps({"subtopics": resolved.get("subtopics", [])})

                # Insert concept — skip if same name already exists for this book+version
                # (happens when LLM extracts the same concept from multiple chunks)
                result = await db.execute(text('''
                    INSERT INTO concepts (id, book_id, name, summary, difficulty_level, graph_version, metadata)
                    VALUES (:id, :book_id, :name, :sum, :diff, :v, :meta)
                    ON CONFLICT (book_id, name, graph_version) DO NOTHING
                    RETURNING id
                '''), {
                    "id": concept_id, "book_id": book_id, "name": resolved["canonical_name"],
                    "sum": resolved["canonical_summary"], "diff": resolved["difficulty"],
                    "v": graph_version_num, "meta": metadata_json
                })
                returned = result.fetchone()
                if returned:
                    # New concept inserted — use generated id
                    canonical_concepts.append(resolved)
                else:
                    # Concept already exists — fetch its real id to use in edges
                    existing = await db.execute(text('''
                        SELECT id FROM concepts
                        WHERE book_id = :book_id AND name = :name AND graph_version = :v
                    '''), {"book_id": book_id, "name": resolved["canonical_name"], "v": graph_version_num})
                    existing_row = existing.fetchone()
                    if existing_row:
                        resolved["id"] = str(existing_row[0])
                    canonical_concepts.append(resolved)
            
            # Stage 5: Extract Relationships
            logger.info("Extracting relationships")
            pairs = CandidatePairGenerator.generate_pairs(canonical_concepts)
            edges = []
            for src_id, tgt_id in pairs:
                src_c = next(c for c in canonical_concepts if c["id"] == src_id)
                tgt_c = next(c for c in canonical_concepts if c["id"] == tgt_id)
                
                # Fetch original chunk content for context
                stmt = text('SELECT content FROM source_chunks WHERE id = :cid')
                res = await db.execute(stmt, {"cid": src_c["source_chunk_id"]})
                content_row = res.fetchone()
                chunk_content = content_row[0] if content_row else ""
                
                rel = self.llm_extractor.extract_relationship(chunk_content, src_c, tgt_c)
                
                # Prerequisite edges form the DAG (kept at moderate confidence).
                # RELATED edges are informational only and tend to be over-produced,
                # so keep just the strongest to avoid a cluttered "hairball" graph.
                keep_edge = (
                    (rel.relationship_type == "PREREQUISITE" and rel.confidence > 0.5)
                    or (rel.relationship_type == "RELATED" and rel.confidence >= 0.85)
                )
                if keep_edge:
                    edge_id = str(uuid.uuid4())
                    edge_dict = {
                        "id": edge_id,
                        "source_concept_id": src_id,
                        "target_concept_id": tgt_id,
                        "relationship_type": rel.relationship_type,
                        "confidence": rel.confidence
                    }
                    edges.append(edge_dict)
                    
                    await db.execute(text('''
                        INSERT INTO concept_edges (id, book_id, graph_version, from_concept_id, to_concept_id, edge_type, confidence)
                        VALUES (:id, :book_id, :v, :src, :tgt, :type, :conf)
                        ON CONFLICT DO NOTHING
                    '''), {
                        "id": edge_id, "book_id": book_id, "v": graph_version_num, "src": src_id, "tgt": tgt_id, "type": rel.relationship_type, "conf": rel.confidence
                    })
            
            # Stage 7: Validate
            logger.info("Validating graph")
            failures = GraphValidator.validate(canonical_concepts, edges)
            
            for f in failures:
                await db.execute(text('''
                    INSERT INTO graph_validation_results (graph_version_id, rule_code, passed, severity, detail)
                    VALUES (:vid, :rc, :pass, :sev, :det)
                '''), {
                    "vid": version_id, "rc": f["rule"], "pass": f["passed"],
                    "sev": f["severity"], "det": json.dumps(f["detail"])
                })
                
            # Stage 8: Repair
            cycles = [f["detail"]["cycles"] for f in failures if f["rule"] == "V01" and not f["passed"]]
            if cycles:
                logger.info("Running repair engine on cycles")
                edges_to_remove = GraphRepair.repair_cycles(cycles[0], edges)
                for edge in edges_to_remove:
                    await db.execute(text('DELETE FROM concept_edges WHERE id = :id'), {"id": edge["id"]})
                    edges.remove(edge)
                    
                    await db.execute(text('''
                        INSERT INTO graph_repair_log (graph_version_id, operation, artifact_id, reason, before_value)
                        VALUES (:vid, 'DELETE_EDGE', :eid, 'CYCLE_REPAIR', :val)
                    '''), {
                        "vid": version_id, "eid": edge["id"], "val": json.dumps(edge)
                    })
            
            # 9. Set to Pending Review
            await db.execute(text('''
                UPDATE books SET status = 'KG_BUILT' WHERE id = :bid
            '''), {"bid": book_id})
            
            await db.execute(text('''
                UPDATE graph_build_jobs SET status = 'COMPLETED', completed_at = NOW(),
                nodes_created = :nodes, edges_created = :edges WHERE id = :job_id
            '''), {"nodes": len(canonical_concepts), "edges": len(edges), "job_id": job_id})
            
            # Source text now lives in source_chunks; the original upload is no
            # longer needed. Delete it unless retention is enabled (re-ingestion).
            from app.core.config import settings
            if not settings.KEEP_SOURCE_FILE:
                try:
                    self.storage_provider.delete(storage_path)
                    await db.execute(text(
                        "UPDATE book_uploads SET upload_status = 'STORED' WHERE storage_path = :p"),
                        {"p": storage_path})
                    logger.info(f"Deleted processed source file: {storage_path}")
                except Exception as del_err:  # noqa: BLE001 - cleanup must not fail the job
                    logger.warning(f"Could not delete source file {storage_path}: {del_err}")

            await db.commit()
            logger.info(f"Job {job_id} completed successfully")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Job {job_id} failed: {str(e)}")
            await db.execute(text('''
                UPDATE graph_build_jobs SET status = 'FAILED', error_message = :err, completed_at = NOW()
                WHERE id = :job_id
            '''), {"err": str(e), "job_id": job_id})
            await db.commit()
            return False
