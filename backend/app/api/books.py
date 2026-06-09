import asyncio
import json
import uuid
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.repositories.book_repo import BookRepository
from app.repositories.graph_repo import GraphRepository
from app.schemas.book import (
    UploadResponse, JobStatusDTO, BookDTO, BookCreate,
    BookStatusDTO, BookDetailDTO, GraphDTO, BookSummaryDTO,
)
from app.schemas.graph_reveal import PersonalGraphDTO
from app.services.book_service import BookService, mock_process_book_job
from app.services.graph_reveal_service import GraphRevealService

router = APIRouter(prefix="/books", tags=["Books"])


def get_book_service(session: AsyncSession = Depends(get_db)) -> BookService:
    return BookService(BookRepository(session))


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models for graph editing (CR: typed models, not raw dict)
# ─────────────────────────────────────────────────────────────────────────────

class DifficultyTier(str, Enum):
    beginner     = "beginner"
    intermediate = "intermediate"
    advanced     = "advanced"


class EdgeType(str, Enum):
    PREREQUISITE = "PREREQUISITE"
    RELATED      = "RELATED"


class CreateNodeRequest(BaseModel):
    title:          str            = Field(..., min_length=1, max_length=300)
    summary:        str            = Field(default="")
    difficultyTier: DifficultyTier = DifficultyTier.beginner
    sectionName:    str | None     = None


class UpdateNodeRequest(BaseModel):
    title:          str | None            = Field(default=None, min_length=1, max_length=300)
    summary:        str | None            = None
    difficultyTier: DifficultyTier | None = None
    sectionName:    str | None            = None


class CreateEdgeRequest(BaseModel):
    fromNodeId:  str       = Field(..., min_length=1)
    toNodeId:    str       = Field(..., min_length=1)
    type:        EdgeType  = EdgeType.PREREQUISITE
    confidence:  float     = Field(default=0.8, ge=0.0, le=1.0)


class UpdateEdgeRequest(BaseModel):
    type:       EdgeType | None = None
    confidence: float | None   = Field(default=None, ge=0.0, le=1.0)


class ChatEditRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _error(code: str, message: str, status: int = 400):
    """Standard error envelope used throughout this repo."""
    raise HTTPException(
        status_code=status,
        detail={"success": False, "error": {"code": code, "message": message}},
    )


async def _assert_owned(session: AsyncSession, user_id: str, book_id: str) -> None:
    check = await session.execute(
        text("SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid"),
        {"uid": user_id, "bid": book_id},
    )
    if not check.fetchone():
        _error("NOT_FOUND", "Book not found in your library", 404)


async def _resolve_active_graph_version(session: AsyncSession, book_id: str) -> int:
    """Return the highest (active) graph_version for this book."""
    row = await session.execute(
        text("SELECT MAX(graph_version) FROM concepts WHERE book_id = :bid"),
        {"bid": book_id},
    )
    gv = row.scalar()
    if gv is None:
        _error("NO_GRAPH", "Knowledge graph not built yet", 409)
    return gv


async def _assert_node_in_book(
    session: AsyncSession, node_id: str, book_id: str, gv: int
) -> None:
    """Verify a concept belongs to this book+version (CR: scope IDs to book)."""
    row = await session.execute(
        text(
            "SELECT 1 FROM concepts "
            "WHERE id = :nid AND book_id = :bid AND graph_version = :gv"
        ),
        {"nid": node_id, "bid": book_id, "gv": gv},
    )
    if not row.fetchone():
        _error("NODE_NOT_FOUND", f"Node {node_id} not found in this book's graph", 404)


# ─────────────────────────────────────────────────────────────────────────────
# Existing endpoints (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=dict, status_code=201)
async def create_book(
    data: BookCreate,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db),
):
    book_dto = await service.create_book(
        user_id, data.title, data.author or "", data.description or "", data.is_public
    )
    await session.commit()
    return {"book": book_dto}


@router.post("/{book_id}/upload", response_model=JobStatusDTO, status_code=202)
async def upload_book_file(
    book_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith((".pdf", ".epub", ".txt")):
        raise HTTPException(status_code=400, detail="Unsupported file format.")
    job_status = await service.upload_book_file(book_id, user_id, file)
    await session.commit()
    return job_status


@router.get("/{book_id}/status", response_model=BookStatusDTO)
async def get_book_status(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
):
    status = await service.get_book_processing_status(book_id)
    if not status:
        raise HTTPException(status_code=404, detail="Book processing status not found")
    return status


@router.get("/{book_id}/graph", response_model=GraphDTO)
async def get_book_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    check = await session.execute(
        text("SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid"),
        {"uid": user_id, "bid": book_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Book not found in your library")
    service = BookService(BookRepository(session))
    return await service.get_book_graph(book_id)


@router.post("/{book_id}/graph/sync-neo4j")
async def sync_graph_to_neo4j(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Project this book's graph + the caller's mastery state into Neo4j."""
    from app.services.neo4j_projection import project_book_graph, project_user_state

    repo = GraphRepository(session)
    if not await repo.is_enrolled(user_id, book_id):
        raise HTTPException(status_code=404, detail="Book not found in your library")
    gv = await repo.active_graph_version(book_id)
    if gv is None:
        raise HTTPException(status_code=409, detail="Knowledge graph not built yet")

    concepts  = await repo.concepts(book_id, gv)
    edges     = await repo.prerequisite_edges(book_id, gv)
    states    = await repo.node_states(user_id, book_id)
    masteries = await repo.masteries(user_id, book_id)

    concept_dicts = [{"id": str(c.id), "name": c.name, "difficulty": c.difficulty_level} for c in concepts]
    edge_tuples   = [(str(e.from_concept_id), str(e.to_concept_id)) for e in edges]
    mastery_rows  = [
        {"concept_id": cid, "score": score, "state": states.get(cid, "")}
        for cid, (score, _lr) in masteries.items()
    ]
    in_progress = [cid for cid, st in states.items() if st == "IN_PROGRESS"]

    book_ok = await project_book_graph(book_id, concept_dicts, edge_tuples)
    user_ok = await project_user_state(user_id, mastery_rows, in_progress)
    return {
        "bookProjected": book_ok, "userProjected": user_ok,
        "concepts": len(concept_dicts), "edges": len(edge_tuples),
    }


@router.get("/{book_id}/knowledge-graph", response_model=PersonalGraphDTO)
async def get_personal_knowledge_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Personalized graph reveal with four-state coloring."""
    service = GraphRevealService(GraphRepository(session))
    return await service.get_personal_graph(user_id, book_id)


@router.post("/{book_id}/graph/confirm")
async def confirm_book_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    await session.execute(
        text("UPDATE books SET status = 'READY' WHERE id = :bid"),
        {"bid": book_id},
    )
    await session.execute(
        text("""
            INSERT INTO user_concept_state (user_id, concept_id, graph_version, state)
            SELECT :uid, c.id, c.graph_version,
                   (CASE WHEN NOT EXISTS (
                        SELECT 1 FROM concept_edges e
                        WHERE e.to_concept_id = c.id
                          AND e.edge_type = 'PREREQUISITE'
                          AND e.book_id = c.book_id
                          AND e.graph_version = c.graph_version
                     ) THEN 'AVAILABLE' ELSE 'LOCKED' END)::node_state
            FROM concepts c
            WHERE c.book_id = :bid
            ON CONFLICT (user_id, concept_id, graph_version) DO NOTHING
        """),
        {"uid": user_id, "bid": book_id},
    )
    await session.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Graph editing — Node CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{book_id}/graph/nodes", status_code=201)
async def create_graph_node(
    book_id: str,
    body: CreateNodeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Create a new concept node in the book's knowledge graph."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)

    title   = body.title.strip()
    summary = body.summary.strip()
    node_id = str(uuid.uuid4())

    try:
        await session.execute(
            text("""
                INSERT INTO concepts
                  (id, book_id, graph_version, name, summary, difficulty_level, section_name, order_index)
                VALUES
                  (:id, :book_id, :gv, :name, :summary, :difficulty, :section, 0)
            """),
            {
                "id":         node_id,
                "book_id":    book_id,
                "gv":         gv,
                "name":       title,
                "summary":    summary,
                "difficulty": body.difficultyTier.value,
                "section":    body.sectionName,
            },
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to create node", 500)

    return {
        "success": True,
        "node": {
            "id":             node_id,
            "title":          title,
            "summary":        summary,
            "difficultyTier": body.difficultyTier.value,
            "sectionName":    body.sectionName,
        },
    }


@router.patch("/{book_id}/graph/nodes/{node_id}")
async def update_graph_node(
    book_id: str,
    node_id: str,
    body: UpdateNodeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Update an existing concept node's title, summary, or difficulty."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)
    await _assert_node_in_book(session, node_id, book_id, gv)

    updates, params = [], {"node_id": node_id, "book_id": book_id, "gv": gv}
    if body.title is not None:
        updates.append("name = :name")
        params["name"] = body.title.strip()
    if body.summary is not None:
        updates.append("summary = :summary")
        params["summary"] = body.summary.strip()
    if body.difficultyTier is not None:
        updates.append("difficulty_level = :difficulty")
        params["difficulty"] = body.difficultyTier.value
    if body.sectionName is not None:
        updates.append("section_name = :section")
        params["section"] = body.sectionName

    if not updates:
        _error("NO_FIELDS", "No fields to update")

    try:
        await session.execute(
            text(
                f"UPDATE concepts SET {', '.join(updates)} "
                f"WHERE id = :node_id AND book_id = :book_id AND graph_version = :gv"
            ),
            params,
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to update node", 500)

    return {"success": True, "node": {"id": node_id, **body.model_dump(exclude_none=True)}}


@router.delete("/{book_id}/graph/nodes/{node_id}", status_code=200)
async def delete_graph_node(
    book_id: str,
    node_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Delete a concept node and all its edges."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)
    await _assert_node_in_book(session, node_id, book_id, gv)

    try:
        # CR: scope edge deletion to this book+version (not across all books)
        await session.execute(
            text("""
                DELETE FROM concept_edges
                WHERE book_id = :bid AND graph_version = :gv
                  AND (from_concept_id = :nid OR to_concept_id = :nid)
            """),
            {"nid": node_id, "bid": book_id, "gv": gv},
        )
        await session.execute(
            text(
                "DELETE FROM concepts "
                "WHERE id = :nid AND book_id = :bid AND graph_version = :gv"
            ),
            {"nid": node_id, "bid": book_id, "gv": gv},
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to delete node", 500)

    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Graph editing — Edge CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{book_id}/graph/edges", status_code=201)
async def create_graph_edge(
    book_id: str,
    body: CreateEdgeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Add a prerequisite edge. Rejects self-loops and cycles."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)

    # CR: validate both nodes belong to this book before using their IDs
    await _assert_node_in_book(session, body.fromNodeId, book_id, gv)
    await _assert_node_in_book(session, body.toNodeId,   book_id, gv)

    # CR: explicit self-loop check before the recursive CTE
    if body.fromNodeId == body.toNodeId:
        _error("SELF_LOOP", "A node cannot be a prerequisite of itself", 409)

    cycle_check = await session.execute(
        text("""
            WITH RECURSIVE reachable AS (
                SELECT to_concept_id AS node_id
                FROM concept_edges
                WHERE from_concept_id = :to_id AND book_id = :bid AND graph_version = :gv
                UNION
                SELECT e.to_concept_id
                FROM concept_edges e
                JOIN reachable r ON e.from_concept_id = r.node_id
                WHERE e.book_id = :bid AND e.graph_version = :gv
            )
            SELECT 1 FROM reachable WHERE node_id = :from_id
        """),
        {"to_id": body.toNodeId, "from_id": body.fromNodeId, "bid": book_id, "gv": gv},
    )
    if cycle_check.fetchone():
        _error("CYCLE_DETECTED", "This edge would create a cycle in the prerequisite graph", 409)

    edge_id = str(uuid.uuid4())
    try:
        await session.execute(
            text("""
                INSERT INTO concept_edges
                  (id, book_id, graph_version, from_concept_id, to_concept_id, edge_type, weight, confidence)
                VALUES
                  (:id, :book_id, :gv, :from_id, :to_id, :edge_type, 1.0, :confidence)
            """),
            {
                "id":         edge_id,
                "book_id":    book_id,
                "gv":         gv,
                "from_id":    body.fromNodeId,
                "to_id":      body.toNodeId,
                "edge_type":  body.type.value,
                "confidence": body.confidence,
            },
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to create edge", 500)

    return {
        "success": True,
        "edge": {
            "id":         edge_id,
            "fromNodeId": body.fromNodeId,
            "toNodeId":   body.toNodeId,
            "type":       body.type.value,
            "confidence": body.confidence,
        },
    }


@router.patch("/{book_id}/graph/edges/{edge_id}")
async def update_graph_edge(
    book_id: str,
    edge_id: str,
    body: UpdateEdgeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Update an edge's type or confidence score."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)

    updates, params = [], {"edge_id": edge_id, "book_id": book_id, "gv": gv}
    if body.type is not None:
        updates.append("edge_type = :edge_type")
        params["edge_type"] = body.type.value
    if body.confidence is not None:
        updates.append("confidence = :confidence")
        params["confidence"] = body.confidence

    if not updates:
        _error("NO_FIELDS", "No fields to update")

    try:
        await session.execute(
            text(
                f"UPDATE concept_edges SET {', '.join(updates)} "
                f"WHERE id = :edge_id AND book_id = :book_id AND graph_version = :gv"
            ),
            params,
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to update edge", 500)

    return {"success": True, "edge": {"id": edge_id, **body.model_dump(exclude_none=True)}}


@router.delete("/{book_id}/graph/edges/{edge_id}", status_code=200)
async def delete_graph_edge(
    book_id: str,
    edge_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Remove an edge from the knowledge graph."""
    await _assert_owned(session, user_id, book_id)
    gv = await _resolve_active_graph_version(session, book_id)

    try:
        await session.execute(
            text(
                "DELETE FROM concept_edges "
                "WHERE id = :eid AND book_id = :bid AND graph_version = :gv"
            ),
            {"eid": edge_id, "bid": book_id, "gv": gv},
        )
        await session.commit()
    except Exception:
        _error("DB_ERROR", "Failed to delete edge", 500)

    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# Graph editing — Chat-based suggestions
# ─────────────────────────────────────────────────────────────────────────────

# CR: prompt centralized (not inline). Template loaded here; file lives at
# backend/app/prompts/graph_editor.md
_GRAPH_EDITOR_PROMPT = """\
You are a knowledge graph editor assistant.

The user wants to edit a knowledge graph. Given their instruction and the current
graph, return a JSON object describing a proposed change for the user to review.
You are a suggestion engine only — the user must confirm before anything changes.

Current nodes (id, title):
{nodes_json}

Current edges (id, from -> to):
{edges_json}

User instruction: "{message}"

Respond ONLY with a JSON object (no markdown, no explanation):
{{
  "action": "delete_node" | "update_node" | "delete_edge" | "create_edge" | "rename_node" | "create_node" | "update_edge",
  "description": "Human-readable summary shown to user for confirmation",
  "nodeId": "uuid if action involves an existing node",
  "edgeId": "uuid if action involves an existing edge",
  "fromNodeId": "uuid if creating an edge",
  "toNodeId": "uuid if creating an edge",
  "newTitle": "new title if creating or renaming a node",
  "newSummary": "new summary if creating or updating a node"
}}

If you cannot match the instruction, return:
{{"action": "unknown", "description": "Could not find matching nodes or edges. Please be more specific."}}
"""


@router.post("/{book_id}/graph/chat")
async def graph_chat_edit(
    book_id: str,
    body: ChatEditRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """
    Parse a plain-English edit suggestion and return a proposed change.
    AI output is suggestion-only — user must confirm before any mutation
    endpoint is called. (CR: AI never updates graph state directly.)
    """
    from google import genai

    await _assert_owned(session, user_id, book_id)
    # CR: resolve active graph_version once; scope all reads to it
    gv = await _resolve_active_graph_version(session, book_id)

    nodes_result = await session.execute(
        text(
            "SELECT id, name FROM concepts "
            "WHERE book_id = :bid AND graph_version = :gv ORDER BY order_index"
        ),
        {"bid": book_id, "gv": gv},
    )
    nodes = [{"id": str(r.id), "title": r.name} for r in nodes_result]

    edges_result = await session.execute(
        text("""
            SELECT e.id, cf.name AS from_name, ct.name AS to_name
            FROM concept_edges e
            JOIN concepts cf ON cf.id = e.from_concept_id
            JOIN concepts ct ON ct.id = e.to_concept_id
            WHERE e.book_id = :bid AND e.graph_version = :gv
        """),
        {"bid": book_id, "gv": gv},
    )
    edges = [
        {"id": str(r.id), "from": r.from_name, "to": r.to_name}
        for r in edges_result
    ]

    prompt = _GRAPH_EDITOR_PROMPT.format(
        nodes_json=json.dumps(nodes, indent=2),
        edges_json=json.dumps(edges, indent=2),
        message=body.message,
    )

    # CR: use settings.GEMINI_MODEL (not hardcoded string)
    # CR: offload blocking call to thread (matches LessonLLM/AssessmentLLM pattern)
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model  = settings.GEMINI_MODEL

    def _call_gemini() -> str:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text.strip()

    try:
        raw = await asyncio.to_thread(_call_gemini)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        proposal = json.loads(raw.strip())
    except json.JSONDecodeError:
        _error("LLM_PARSE_ERROR", "The AI returned an unexpected format. Try rephrasing.", 500)
    except Exception:
        _error("LLM_ERROR", "AI service unavailable. Please try again.", 500)

    return {"success": True, "proposal": proposal}


# ─────────────────────────────────────────────────────────────────────────────
# Book library endpoints (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def get_user_books(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = BookService(BookRepository(session))
    books   = await service.book_repo.get_books_by_user(user_id)
    summaries = []
    for b in books:
        status_str = getattr(b, "status", "UPLOADING").lower()
        if status_str == "uploading":
            status_str = "uploaded"
        summaries.append(
            BookSummaryDTO(
                id=str(b.id),
                title=b.title,
                author=b.author,
                coverUrl=None,
                status=status_str,
                progress=0,
                totalNodes=0,
                masteredNodes=0,
                dueToday=0,
                lastStudied=None,
                createdAt=b.created_at.isoformat(),
            ).model_dump(by_alias=True)
        )
    return {"books": summaries}


@router.get("/{book_id}", response_model=dict)
async def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service   = BookService(BookRepository(session))
    user_book = await service.book_repo.get_user_book(user_id, book_id)
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not found in your library")

    book = await service.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    states = await session.execute(
        text("""
            SELECT ucs.concept_id, ucs.state
            FROM user_concept_state ucs
            JOIN concepts c ON c.id = ucs.concept_id
            WHERE ucs.user_id = :uid AND c.book_id = :bid
        """),
        {"uid": user_id, "bid": book_id},
    )
    nodes = [
        {"id": str(r.concept_id), "userNodeStates": [{"nodeId": str(r.concept_id), "state": r.state}]}
        for r in states
    ]
    return {
        "book": BookDetailDTO(
            id=str(book.id),
            title=book.title,
            author=book.author,
            description=book.description,
            source_type=book.source_type,
            file_url=book.file_url,
            created_at=book.created_at,
            nodes=nodes,
        ).model_dump()
    }


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        text("""
            SELECT ub.id, b.owner_id
            FROM user_books ub
            JOIN books b ON b.id = ub.book_id
            WHERE ub.user_id = :uid AND ub.book_id = :bid
        """),
        {"uid": user_id, "bid": book_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Book not found in your library")

    user_book_id, owner_id = row
    await session.execute(
        text("DELETE FROM user_books WHERE id = :id"),
        {"id": str(user_book_id)},
    )
    if str(owner_id) == user_id:
        await session.execute(
            text("DELETE FROM books WHERE id = :id"),
            {"id": book_id},
        )
    await session.commit()
    return None