"""
Personalized knowledge-graph reveal (System Design Section E).

Overlays each concept with the current user's learning state + mastery so the
frontend can render the four-state map (LOCKED / AVAILABLE / IN_PROGRESS /
MASTERED / DUE). Read-only.

If the user has no per-concept state yet (e.g. before assessment), a sensible
default reveal is computed from the DAG: root concepts (no prerequisites) are
AVAILABLE, everything downstream is LOCKED.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException

from app.repositories.graph_repo import GraphRepository
from app.schemas.graph_reveal import (
    GraphNodeStateDTO, GraphRevealEdgeDTO, GraphRevealSummaryDTO, PersonalGraphDTO,
)


class GraphRevealService:
    def __init__(self, repo: GraphRepository):
        self.repo = repo

    async def get_personal_graph(self, user_id: str, book_id: str) -> PersonalGraphDTO:
        if not await self.repo.is_enrolled(user_id, book_id):
            raise HTTPException(status_code=404, detail="Book not found in your library.")

        gv = await self.repo.active_graph_version(book_id)
        if gv is None:
            raise HTTPException(status_code=409, detail="Knowledge graph not built for this book yet.")

        concepts = await self.repo.concepts(book_id, gv)
        edges = await self.repo.prerequisite_edges(book_id, gv)
        states = await self.repo.node_states(user_id, book_id)
        masteries = await self.repo.masteries(user_id, book_id)
        due = await self.repo.next_due(user_id, book_id)

        direct_prereqs: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            direct_prereqs[str(e.to_concept_id)].append(str(e.from_concept_id))

        nodes: List[GraphNodeStateDTO] = []
        counts = {"LOCKED": 0, "AVAILABLE": 0, "IN_PROGRESS": 0, "MASTERED": 0, "DUE": 0}

        for c in concepts:
            cid = str(c.id)
            if cid in states:
                state = states[cid]
            else:
                # Default reveal: roots are available, dependents locked.
                state = "AVAILABLE" if not direct_prereqs.get(cid) else "LOCKED"
            counts[state] = counts.get(state, 0) + 1

            score, last_reviewed = masteries.get(cid, (0.0, None))
            nodes.append(GraphNodeStateDTO(
                id=cid,
                title=c.name,
                summary=c.summary,
                difficulty=c.difficulty_level,
                state=state,
                masteryScore=score,
                lastReviewed=last_reviewed,
                nextDue=due.get(cid),
                prerequisites=direct_prereqs.get(cid, []),
            ))

        edge_dtos = [
            GraphRevealEdgeDTO(
                fromNodeId=str(e.from_concept_id),
                toNodeId=str(e.to_concept_id),
                type=e.edge_type,
            )
            for e in edges
        ]

        total = len(concepts)
        revealed = total - counts["LOCKED"]
        summary = GraphRevealSummaryDTO(
            total=total,
            mastered=counts["MASTERED"],
            available=counts["AVAILABLE"],
            inProgress=counts["IN_PROGRESS"],
            due=counts["DUE"],
            locked=counts["LOCKED"],
            percentMastered=round(100.0 * counts["MASTERED"] / total, 1) if total else 0.0,
            percentRevealed=round(100.0 * revealed / total, 1) if total else 0.0,
        )

        return PersonalGraphDTO(nodes=nodes, edges=edge_dtos, summary=summary)
