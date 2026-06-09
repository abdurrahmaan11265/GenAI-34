"""
Neo4j repository for read-only graph topology traversals.
"""
from __future__ import annotations

import asyncio
from typing import List

from app.core.neo4j import Neo4jDriver


def _get_topological_order_sync(book_id: str) -> List[str]:
    """
    Returns a list of concept IDs topologically sorted (roots first).
    Nodes with longer paths to the leaves appear earlier.
    """
    driver = Neo4jDriver.get_driver()
    with driver.session() as s:
        result = s.run(
            """
            MATCH (c:Concept {book_id: $book_id})
            OPTIONAL MATCH p=(c)-[:PREREQUISITE_OF*]->()
            RETURN c.id AS id, coalesce(max(length(p)), 0) AS depth
            ORDER BY depth DESC, c.id ASC
            """,
            book_id=book_id,
        )
        return [record["id"] for record in result]


def _get_descendants_sync(book_id: str, concept_ids: List[str]) -> List[str]:
    """
    Returns all concept IDs that are transitive dependents of the given concept_ids.
    (i.e., everything downstream via PREREQUISITE_OF relationships).
    """
    if not concept_ids:
        return []

    driver = Neo4jDriver.get_driver()
    with driver.session() as s:
        result = s.run(
            """
            MATCH (failed:Concept {book_id: $book_id})
            WHERE failed.id IN $concept_ids
            MATCH (failed)-[:PREREQUISITE_OF*]->(descendant:Concept)
            RETURN DISTINCT descendant.id AS id
            """,
            book_id=book_id,
            concept_ids=concept_ids,
        )
        return [record["id"] for record in result]


class Neo4jRepository:
    """Async wrapper for the Neo4j runtime topology operations."""

    async def get_topological_order(self, book_id: str) -> List[str]:
        return await asyncio.to_thread(_get_topological_order_sync, book_id)

    async def get_descendants(self, book_id: str, concept_ids: List[str]) -> List[str]:
        return await asyncio.to_thread(_get_descendants_sync, book_id, concept_ids)
