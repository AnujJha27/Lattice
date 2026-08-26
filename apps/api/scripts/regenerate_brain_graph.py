"""Produce a reviewable AI graph audit. Never mutates the database."""
import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db.session import create_db_engine
from app.providers.factory import get_llm_provider


class ProposedEdge(BaseModel):
    source: str
    target: str
    type: str = Field(pattern="^(PREREQUISITE|RELATED_TO)$")
    confidence: float = Field(ge=0, le=1)


class PathwayAudit(BaseModel):
    domains: dict[str, str]
    edges: list[ProposedEdge]


SYSTEM = """You audit a learning graph. Assign every concept a concise broad domain.
Return only defensible relations among supplied concepts. PREREQUISITE means source
must be learned before target; RELATED_TO is a non-hierarchical semantic association.
Do not invent names, do not connect unrelated subjects, and use confidence below 0.85
only when the relationship is uncertain."""


async def main(report_path: Path) -> None:
    engine = create_db_engine()
    async with engine.connect() as connection:
        rows = await connection.execute(text("""
            SELECT p.id AS pathway_id, p.title, c.id AS concept_id, c.canonical_name,
                   c.description, ps.position AS section
            FROM pathways p
            JOIN pathway_concepts pc ON pc.pathway_id = p.id
            JOIN concepts c ON c.id = pc.concept_id
            LEFT JOIN pathway_sections ps ON ps.id = pc.section_id
            ORDER BY p.id, ps.position, pc.position
        """))
        pathways: dict[str, list[dict]] = defaultdict(list)
        titles: dict[str, str] = {}
        for row in rows.mappings():
            pathway_id = str(row["pathway_id"])
            titles[pathway_id] = row["title"]
            pathways[pathway_id].append(dict(row))

    provider = get_llm_provider()
    print(f"Auditing {len(pathways)} pathways with {provider.provider_name}", flush=True)
    report: dict[str, object] = {"pathways": {}, "apply": False}
    for pathway_id, concepts in pathways.items():
        print(f"Auditing {titles[pathway_id]} ({len(concepts)} concepts)", flush=True)
        prompt = "Pathway: " + titles[pathway_id] + "\nConcepts:\n" + "\n".join(
            f"- {c['canonical_name']} (section {c['section'] or 0}): {c['description'] or ''}"
            for c in concepts
        )
        response = await provider.generate_structured(prompt, PathwayAudit, system=SYSTEM)
        audit = PathwayAudit.model_validate(response.structured)
        known = {c["canonical_name"] for c in concepts}
        section = {c["canonical_name"]: c["section"] or 0 for c in concepts}
        edges = [
            edge.model_dump()
            for edge in audit.edges
            if edge.source in known and edge.target in known and edge.source != edge.target
            and (edge.type != "PREREQUISITE" or section[edge.source] < section[edge.target])
        ]
        report["pathways"][pathway_id] = {
            "title": titles[pathway_id],
            "domains": {name: " ".join(domain.split()) for name, domain in audit.domains.items() if name in known and domain.strip()},
            "edges": edges,
        }
    await engine.dispose()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote dry-run report: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path("brain-edge-audit.json"))
    args = parser.parse_args()
    asyncio.run(main(args.report))
