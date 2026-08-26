"""Backfill missing concept domains from their pathways, then direct neighbours."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db.session import create_db_engine


async def main() -> None:
    engine = create_db_engine()
    async with engine.begin() as connection:
        from_pathways = await connection.execute(text("""
            WITH domains AS (
                SELECT pc.concept_id, min(p.title) AS domain
                FROM pathway_concepts pc JOIN pathways p ON p.id = pc.pathway_id
                GROUP BY pc.concept_id
            )
            UPDATE concepts c SET domain = domains.domain
            FROM domains WHERE c.id = domains.concept_id AND c.domain IS NULL
        """))
        from_neighbours = await connection.execute(text("""
            UPDATE concepts c SET domain = neighbour.domain
            FROM concept_edges e, concepts neighbour
            WHERE c.domain IS NULL
              AND ((e.source_id = c.id AND neighbour.id = e.target_id)
                   OR (e.target_id = c.id AND neighbour.id = e.source_id))
              AND neighbour.domain IS NOT NULL
        """))
    await engine.dispose()
    print(f"pathway domains: {from_pathways.rowcount}; linked domains: {from_neighbours.rowcount}")


asyncio.run(main())
