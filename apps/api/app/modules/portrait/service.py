"""Deterministic portrait analysis over the user's existing Lattice graph."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.models import (
    Concept,
    ConceptEdge,
    Goal,
    GoalConcept,
    PortraitSnapshot,
    Review,
    UserConcept,
)
from app.db.models.concept import EdgeType
from app.db.models.learning import GoalStatus
from app.modules.portrait.schemas import (
    PortraitChange,
    PortraitConnection,
    PortraitDomain,
    PortraitModel,
    PortraitNode,
    PortraitSummary,
    PortraitThread,
)
from app.modules.visual_sources.service import with_visual_sources

logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "portrait-1"
CONFIG_VERSION = "portrait-defaults-2"


@dataclass(frozen=True, slots=True)
class PortraitConfig:
    """Tunable portrait thresholds and normalized scoring weights."""

    min_interactions: int = 10
    anchor_mastery_threshold: float = 0.7
    anchor_min_interactions: int = 2
    prerequisite_mastery_threshold: float = 0.6
    frontier_mastery_ceiling: float = 0.85
    recent_days: int = 30
    recency_decay_days: float = 30.0
    dormant_days: int = 42
    emerging_min_concepts: int = 3
    emerging_min_interactions: int = 3
    activity_interaction_target: float = 8.0
    reinforcement_success_target: float = 5.0
    connectivity_degree_target: float = 6.0
    emerging_interaction_target: float = 12.0
    bridge_domain_target: float = 3.0
    dormant_interaction_target: float = 20.0
    breadth_concept_target: float = 8.0
    confidence_interaction_target: float = 30.0
    recent_review_days: int = 30
    domain_weights: tuple[float, float, float, float, float] = (0.3, 0.25, 0.2, 0.15, 0.1)
    depth_weights: tuple[float, float] = (0.75, 0.25)
    dominant_concept_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
    anchor_weights: tuple[float, float, float, float] = (0.45, 0.25, 0.15, 0.15)
    frontier_weights: tuple[float, float, float, float, float] = (0.3, 0.25, 0.2, 0.15, 0.1)
    bridge_weights: tuple[float, float, float] = (0.4, 0.3, 0.3)
    emerging_weights: tuple[float, float] = (0.5, 0.5)


PORTRAIT_CONFIG = PortraitConfig()


def stable_input_hash(
    records: list[dict[str, Any]],
    edges: list[tuple[Any, ...]],
    context: dict[str, Any] | None = None,
) -> str:
    payload = {
        "context": context or {},
        "records": sorted(records, key=lambda record: str(record.get("id", ""))),
        "edges": sorted(tuple(edge) for edge in edges),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def anchor_score(
    mastery: float,
    activity: float,
    reinforcement: float,
    connectivity: float,
    config: PortraitConfig | None = None,
) -> float:
    mastery_weight, activity_weight, reinforcement_weight, connectivity_weight = (
        (config or PORTRAIT_CONFIG).anchor_weights
    )
    return round(
        mastery_weight * mastery
        + activity_weight * activity
        + reinforcement_weight * reinforcement
        + connectivity_weight * connectivity,
        3,
    )


def frontier_score(
    interest: float,
    recency: float,
    readiness: float,
    activity: float,
    mastery: float,
    config: PortraitConfig | None = None,
) -> float:
    interest_weight, recency_weight, readiness_weight, activity_weight, unmastered_weight = (
        (config or PORTRAIT_CONFIG).frontier_weights
    )
    return round(
        interest_weight * interest
        + recency_weight * recency
        + readiness_weight * readiness
        + activity_weight * activity
        + unmastered_weight * (1 - mastery),
        3,
    )


def _debug_factor(name: str, value: float, weight: float) -> dict[str, float | str]:
    return {
        "name": name,
        "value": round(value, 3),
        "weight": weight,
        "contribution": round(value * weight, 3),
    }


def _debug_entry(
    debug: list[dict[str, Any]] | None,
    *,
    kind: str,
    element_id: str,
    name: str,
    score: float,
    threshold: str,
    selected: bool,
    factors: list[dict[str, float | str]],
) -> None:
    if debug is not None:
        debug.append({
            "kind": kind,
            "id": element_id,
            "name": name,
            "score": round(score, 3),
            "threshold": threshold,
            "selected": selected,
            "factors": factors,
        })


def is_emerging_thread(
    concept_count: int,
    recent_interactions: int,
    config: PortraitConfig | None = None,
) -> bool:
    active_config = config or PORTRAIT_CONFIG
    return (
        concept_count >= active_config.emerging_min_concepts
        and recent_interactions >= active_config.emerging_min_interactions
    )


def has_portrait_evidence(interactions: int, config: PortraitConfig | None = None) -> bool:
    return interactions >= (config or PORTRAIT_CONFIG).min_interactions


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _domain_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug or "uncategorized"


def _days_since(value: datetime | None, now: datetime) -> float | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return max(0.0, (now - value).total_seconds() / 86_400)


def _last_activity(state: UserConcept) -> datetime | None:
    return max(
        (value for value in (state.last_seen_at, state.last_tested_at) if value is not None),
        default=None,
    )


def _facts(
    concept: Concept,
    state: UserConcept,
    now: datetime,
    config: PortraitConfig | None = None,
) -> dict[str, Any]:
    active_config = config or PORTRAIT_CONFIG
    mastery = _clamp(float(state.mastery_score or 0) / 100)
    interest = _clamp(float(state.interest_score or 0) / 100)
    interactions = max(int(state.attempt_count or 0), int(state.review_count or 0))
    successful = int(state.successful_reviews or 0)
    activity = _clamp(interactions / active_config.activity_interaction_target)
    reinforcement = _clamp(successful / active_config.reinforcement_success_target)
    last_activity = _last_activity(state)
    days = _days_since(last_activity, now)
    recency = (
        math.exp(-(days if days is not None else 365) / active_config.recency_decay_days)
        if last_activity else 0.0
    )
    return {
        "id": str(concept.id),
        "name": concept.canonical_name,
        "domain": (concept.domain or "Uncategorized").strip() or "Uncategorized",
        "mastery": mastery,
        "interest": interest,
        "interactions": interactions,
        "reinforcement": reinforcement,
        "activity": activity,
        "recency": recency,
        "recent": bool(days is not None and days <= active_config.recent_days),
        "last_activity": last_activity.isoformat() if last_activity else None,
    }


def _node(fact: dict[str, Any], score: float, reason: str, connected_domains: set[str] | None = None) -> PortraitNode:
    return PortraitNode(
        id=fact["id"], name=fact["name"], domain=fact["domain"], score=round(score, 3),
        mastery=round(fact["mastery"], 3), activity=round(fact["activity"], 3),
        reason=reason, connected_domains=sorted(connected_domains or set()),
    )


def _changes(previous: dict[str, Any] | None, model: PortraitModel) -> list[PortraitChange]:
    if not previous:
        return []
    changes: list[PortraitChange] = []
    for key, label in (("emerging_threads", "Emerging thread"), ("frontiers", "Frontier"), ("bridges", "Bridge")):
        old = {item.get("name") for item in previous.get(key, [])}
        current = {item.name for item in getattr(model, key)}
        for item in getattr(model, key):
            if item.name not in old:
                changes.append(PortraitChange(kind=key[:-1], text=f"{label} appeared: {item.name}"))
        for name in sorted(old - current):
            changes.append(PortraitChange(kind=key[:-1], text=f"{label} receded: {name}"))
    return changes[:8]


def _narrative(
    summary: PortraitSummary,
    bridges: list[PortraitNode],
    frontiers: list[PortraitNode],
    emerging: list[PortraitThread],
    evidence_count: int | None = None,
    config: PortraitConfig | None = None,
) -> str:
    if summary.concept_count == 0 or (
        evidence_count is not None and not has_portrait_evidence(evidence_count, config)
    ):
        return "Your portrait is still forming. Build a few more meaningful interactions to reveal its shape."
    sentences = [
        f"{summary.dominant_domains[0]} is currently your most developed domain, with {summary.concept_count} concepts across {summary.domain_count} areas."
    ]
    if bridges:
        bridge = bridges[0]
        sentences.append(f"{bridge.name} is your strongest visible bridge, connecting {', '.join(bridge.connected_domains)}.")
    if frontiers:
        sentences.append(f"{frontiers[0].name} currently sits near your learning frontier.")
    elif emerging:
        sentences.append(f"{emerging[0].name} is the clearest emerging thread in your recent activity.")
    return " ".join(sentences[:3])


async def build_portrait(
    session: AsyncSession,
    user: CurrentUser,
    now: datetime | None = None,
    debug: list[dict[str, Any]] | None = None,
    config: PortraitConfig | None = None,
) -> PortraitModel:
    now = now or datetime.now(UTC)
    config = config or PORTRAIT_CONFIG
    pairs = (await session.execute(
        select(Concept, UserConcept).join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id)
    )).all()
    facts = {str(concept.id): _facts(concept, state, now, config) for concept, state in pairs}
    states = {str(concept.id): state for concept, state in pairs}
    if not facts:
        summary = PortraitSummary(concept_count=0, mastered_concept_count=0, domain_count=0, active_frontier_count=0)
        return PortraitModel(
            snapshot_id="", generated_at=now, version=1, algorithm_version=ALGORITHM_VERSION,
            config_version=CONFIG_VERSION,
            input_hash=stable_input_hash([], [], context={
                "algorithm_version": ALGORITHM_VERSION,
                "config_version": CONFIG_VERSION,
                "scoring_config": asdict(config),
                "active_goal_ids": [],
            }),
            summary=summary,
            narrative=_narrative(summary, [], [], [], config=config), confidence={"overall": 0},
        )

    ids = [UUID(concept_id) for concept_id in facts]
    edge_rows = (await session.execute(select(ConceptEdge).where(
        ConceptEdge.source_id.in_(ids), ConceptEdge.target_id.in_(ids),
        ConceptEdge.type.in_([EdgeType.RELATED_TO, EdgeType.PREREQUISITE]),
    ))).scalars().all()
    edges = [
        (str(edge.source_id), str(edge.target_id), edge.type.value,
         float(edge.confidence) if edge.confidence is not None else None)
        for edge in edge_rows
    ]
    adjacency: dict[str, set[str]] = {concept_id: set() for concept_id in facts}
    prerequisites: dict[str, set[str]] = {concept_id: set() for concept_id in facts}
    cross_domains: dict[str, set[str]] = {concept_id: set() for concept_id in facts}
    connections = []
    for edge in edge_rows:
        source_id, target_id = str(edge.source_id), str(edge.target_id)
        adjacency[source_id].add(target_id)
        adjacency[target_id].add(source_id)
        if edge.type == EdgeType.PREREQUISITE:
            prerequisites[target_id].add(source_id)
        if facts[source_id]["domain"] != facts[target_id]["domain"]:
            cross_domains[source_id].add(facts[target_id]["domain"])
            cross_domains[target_id].add(facts[source_id]["domain"])
        connections.append(PortraitConnection(
            source_id=source_id, target_id=target_id, type=edge.type.value,
            confidence=float(edge.confidence) if edge.confidence is not None else None,
        ))

    goal_ids = {
        str(concept_id) for concept_id in (await session.execute(
            select(GoalConcept.concept_id).join(Goal, Goal.id == GoalConcept.goal_id)
            .where(Goal.user_id == user.id, Goal.status == GoalStatus.ACTIVE)
        )).scalars().all()
    }
    for concept_id, fact in facts.items():
        fact["connectivity"] = _clamp(len(adjacency[concept_id]) / config.connectivity_degree_target)
        fact["readiness"] = float(bool(prerequisites[concept_id])) and float(all(
            source_id in states
            and _clamp(float(states[source_id].mastery_score or 0) / 100)
            >= config.prerequisite_mastery_threshold
            for source_id in prerequisites[concept_id]
        ))

    domains: dict[str, list[dict[str, Any]]] = {}
    for fact in facts.values():
        domains.setdefault(fact["domain"], []).append(fact)
    domain_models = []
    for name, items in domains.items():
        mastery = sum(item["mastery"] for item in items) / len(items)
        activity = sum(item["activity"] for item in items) / len(items)
        interest = sum(item["interest"] for item in items) / len(items)
        recency = sum(item["recency"] for item in items) / len(items)
        breadth = _clamp(len(items) / config.breadth_concept_target)
        depth_mastery_weight, depth_prerequisite_weight = config.depth_weights
        depth = _clamp(
            depth_mastery_weight * mastery
            + depth_prerequisite_weight * sum(bool(prerequisites[item["id"]]) for item in items) / len(items)
        )
        mastery_weight, activity_weight, interest_weight, recency_weight, breadth_weight = config.domain_weights
        weight = _clamp(
            mastery_weight * mastery
            + activity_weight * activity
            + interest_weight * interest
            + recency_weight * recency
            + breadth_weight * breadth
        )
        top_mastery_weight, top_activity_weight, top_interest_weight = config.dominant_concept_weights
        top = sorted(
            items,
            key=lambda item: (
                top_mastery_weight * item["mastery"]
                + top_activity_weight * item["activity"]
                + top_interest_weight * item["interest"],
                item["id"],
            ),
            reverse=True,
        )
        domain_models.append(PortraitDomain(
            id=_domain_id(name), name=name, concept_count=len(items), mastery=round(mastery, 3),
            activity=round(activity, 3), interest=round(interest, 3), recency=round(recency, 3),
            breadth=round(breadth, 3), depth=round(depth, 3), portrait_weight=round(weight, 3),
            dominant_concept_ids=[item["id"] for item in top[:5]],
        ))
    domain_models.sort(key=lambda item: (-item.portrait_weight, item.name))

    anchors = []
    for fact in facts.values():
        score = anchor_score(
            fact["mastery"], fact["activity"], fact["reinforcement"], fact["connectivity"], config
        )
        selected = (
            fact["mastery"] >= config.anchor_mastery_threshold
            and fact["interactions"] >= config.anchor_min_interactions
        )
        _debug_entry(
            debug, kind="anchor", element_id=fact["id"], name=fact["name"], score=score,
            threshold=(
                f"mastery >= {config.anchor_mastery_threshold:.2f} "
                f"and interactions >= {config.anchor_min_interactions}"
            ), selected=selected,
            factors=[
                _debug_factor("mastery", fact["mastery"], config.anchor_weights[0]),
                _debug_factor("activity", fact["activity"], config.anchor_weights[1]),
                _debug_factor("reinforcement", fact["reinforcement"], config.anchor_weights[2]),
                _debug_factor("connectivity", fact["connectivity"], config.anchor_weights[3]),
            ],
        )
        if selected:
            anchors.append(_node(fact, score, "Established through mastery and repeated interaction"))
    anchors.sort(key=lambda item: (-item.score, item.name))

    frontiers = []
    for fact in facts.values():
        score = frontier_score(
            fact["interest"], fact["recency"], fact["readiness"], fact["activity"], fact["mastery"], config
        )
        selected = fact["mastery"] < config.frontier_mastery_ceiling and (
            fact["recent"] or fact["readiness"] or fact["id"] in goal_ids
        )
        _debug_entry(
            debug, kind="frontier", element_id=fact["id"], name=fact["name"], score=score,
            threshold=(
                f"mastery < {config.frontier_mastery_ceiling:.2f} and recent, "
                "ready, or active goal"
            ), selected=selected,
            factors=[
                _debug_factor("interest", fact["interest"], config.frontier_weights[0]),
                _debug_factor("recency", fact["recency"], config.frontier_weights[1]),
                _debug_factor("readiness", fact["readiness"], config.frontier_weights[2]),
                _debug_factor("activity", fact["activity"], config.frontier_weights[3]),
                _debug_factor("unmastered", 1 - fact["mastery"], config.frontier_weights[4]),
            ],
        )
        if selected:
            reasons = []
            if fact["id"] in goal_ids:
                reasons.append("active goal")
            if fact["readiness"]:
                reasons.append("prerequisites ready")
            if fact["recent"]:
                reasons.append("recent activity")
            frontiers.append(_node(fact, score, f"Near your frontier through {', '.join(reasons)}"))
    frontiers.sort(key=lambda item: (-item.score, item.name))

    bridges = []
    for fact in facts.values():
        domain_coverage = min(1, len(cross_domains[fact["id"]]) / config.bridge_domain_target)
        cross_domain_weight, mastery_weight, activity_weight = config.bridge_weights
        score = _clamp(
            cross_domain_weight * domain_coverage
            + mastery_weight * fact["mastery"]
            + activity_weight * fact["activity"]
        )
        selected = bool(cross_domains[fact["id"]])
        _debug_entry(
            debug, kind="bridge", element_id=fact["id"], name=fact["name"], score=score,
            threshold="at least one cross-domain connection", selected=selected,
            factors=[
                _debug_factor("cross-domain coverage", domain_coverage, config.bridge_weights[0]),
                _debug_factor("mastery", fact["mastery"], config.bridge_weights[1]),
                _debug_factor("activity", fact["activity"], config.bridge_weights[2]),
            ],
        )
        if not selected:
            continue
        bridges.append(_node(
            fact, score, f"Connects {len(cross_domains[fact['id']])} domains in your Brain", cross_domains[fact["id"]]
        ))
    bridges.sort(key=lambda item: (-item.score, item.name))

    emerging = []
    dormant = []
    for name, items in domains.items():
        recent_concepts = [item for item in items if item["recent"]]
        recent_interactions = sum(item["interactions"] for item in recent_concepts)
        recent_concept_weight, recent_interaction_weight = config.emerging_weights
        emerging_score = round(_clamp(
            recent_concept_weight * len(recent_concepts) / len(items)
            + recent_interaction_weight * recent_interactions / config.emerging_interaction_target
        ), 3)
        emerging_selected = is_emerging_thread(len(recent_concepts), recent_interactions, config)
        _debug_entry(
            debug, kind="emerging_thread", element_id=_domain_id(name), name=name, score=emerging_score,
            threshold=(
                f"at least {config.emerging_min_concepts} recent concepts and "
                f"{config.emerging_min_interactions} recent interactions"
            ), selected=emerging_selected,
            factors=[
                _debug_factor("recent concept ratio", len(recent_concepts) / len(items), config.emerging_weights[0]),
                _debug_factor(
                    "recent interaction ratio",
                    recent_interactions / config.emerging_interaction_target,
                    config.emerging_weights[1],
                ),
            ],
        )
        if emerging_selected:
            emerging.append(PortraitThread(
                id=_domain_id(name), name=name,
                score=emerging_score,
                concept_ids=[item["id"] for item in recent_concepts],
                reason=f"{len(recent_concepts)} related concepts show {recent_interactions} recent interactions",
            ))
        historical = sum(item["interactions"] for item in items)
        dormant_selected = (
            len(items) >= config.emerging_min_concepts
            and historical >= config.emerging_min_interactions
            and not recent_concepts
            and all(
                (
                    item["last_activity"] is not None
                    and _days_since(datetime.fromisoformat(item["last_activity"]), now) > config.dormant_days
                )
                for item in items
            )
        )
        dormant_score = round(_clamp(historical / config.dormant_interaction_target), 3)
        _debug_entry(
            debug, kind="dormant_thread", element_id=_domain_id(name), name=name, score=dormant_score,
            threshold=(
                f"{config.emerging_min_concepts} concepts, {config.emerging_min_interactions} interactions, "
                f"no recent concepts, and >{config.dormant_days} days inactive"
            ),
            selected=dormant_selected,
            factors=[_debug_factor("historical interaction ratio", historical / config.dormant_interaction_target, 1.0)],
        )
        if dormant_selected:
            dormant.append(PortraitThread(
                id=_domain_id(name), name=name, score=dormant_score,
                concept_ids=[item["id"] for item in items], reason=f"Little activity in the last {config.dormant_days} days",
            ))
    emerging.sort(key=lambda item: (-item.score, item.name))
    dormant.sort(key=lambda item: (-item.score, item.name))

    evidence_count = sum(fact["interactions"] for fact in facts.values())
    if not has_portrait_evidence(evidence_count, config):
        anchors = []
        bridges = []
        frontiers = []
        emerging = []
        dormant = []
        if debug is not None:
            for entry in debug:
                entry["selected"] = False
                entry["suppressed_by_evidence"] = True

    recent_reviews = (await session.execute(select(Review).where(
        Review.user_id == user.id, Review.created_at >= now - timedelta(days=config.recent_review_days)
    ))).scalars().all()
    mastered_count = sum(fact["mastery"] >= config.anchor_mastery_threshold for fact in facts.values())
    sparse = not has_portrait_evidence(evidence_count, config)
    summary = PortraitSummary(
        concept_count=len(facts), mastered_concept_count=mastered_count, domain_count=len(domains),
        active_frontier_count=len(frontiers),
        dominant_domains=[] if sparse else [domain.name for domain in domain_models[:5]],
        strongest_thread=None if sparse or not domain_models else domain_models[0].name,
        emerging_thread=None if sparse or not emerging else emerging[0].name,
        primary_bridge=None if sparse or not bridges else bridges[0].name,
        primary_frontier=None if sparse or not frontiers else frontiers[0].name,
    )
    records = [
        {key: fact[key] for key in (
            "id", "name", "domain", "mastery", "interest", "interactions", "reinforcement", "last_activity"
        )}
        for fact in facts.values()
    ]
    input_hash = stable_input_hash(records, edges, context={
        "algorithm_version": ALGORITHM_VERSION,
        "config_version": CONFIG_VERSION,
        "scoring_config": asdict(config),
        "active_goal_ids": sorted(goal_ids),
    })
    overall = _clamp(sum(fact["interactions"] for fact in facts.values()) / config.confidence_interaction_target)
    confidence = {
        "overall": round(overall, 3),
        "anchor": round(_clamp(sum(item.score for item in anchors) / max(1, len(anchors))), 3),
        "bridge": round(_clamp(sum(item.score for item in bridges) / max(1, len(bridges))), 3),
        "frontier": round(_clamp(sum(item.score for item in frontiers) / max(1, len(frontiers))), 3),
        "emerging_thread": round(_clamp(sum(item.score for item in emerging) / max(1, len(emerging))), 3),
    }
    return PortraitModel(
        snapshot_id="", generated_at=now, version=1, algorithm_version=ALGORITHM_VERSION,
        config_version=CONFIG_VERSION, input_hash=input_hash, summary=summary, domains=domain_models,
        anchors=anchors[:12], bridges=bridges[:12], frontiers=frontiers[:12], emerging_threads=emerging[:8],
        dormant_threads=dormant[:8], connections=connections[:100],
        evolution={
            "concepts": len(facts),
            "mastered": mastered_count,
            "reviews": sum(int(state.review_count or 0) for state in states.values()),
            "recent_reviews": len(recent_reviews),
            "mastery_delta": round(sum(float(review.mastery_after) - float(review.previous_mastery) for review in recent_reviews), 1),
        }, narrative=_narrative(summary, bridges, frontiers, emerging, evidence_count, config), confidence=confidence,
    )


def _stored_model(snapshot: PortraitSnapshot) -> PortraitModel | None:
    try:
        return PortraitModel.model_validate({**snapshot.payload, "snapshot_id": str(snapshot.id), "generated_at": snapshot.created_at})
    except Exception:
        return None


async def get_portrait(
    session: AsyncSession,
    user: CurrentUser,
    *,
    recompute: bool = True,
    fallback_on_error: bool = True,
) -> PortraitModel:
    latest = (await session.execute(
        select(PortraitSnapshot).where(PortraitSnapshot.user_id == user.id)
        .order_by(PortraitSnapshot.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    stored = _stored_model(latest) if latest else None
    if not recompute and stored:
        return await with_visual_sources(session, stored)
    try:
        model = await build_portrait(session, user)
    except Exception:
        await session.rollback()
        fallback = _stored_model(latest) if latest else None
        if fallback and fallback_on_error:
            logger.exception("portrait computation failed; serving previous snapshot")
            return await with_visual_sources(session, fallback)
        raise
    if stored and stored.input_hash == model.input_hash:
        return await with_visual_sources(session, stored)
    changes = _changes(latest.payload if latest else None, model)
    if stored and not changes and (
        stored.algorithm_version == model.algorithm_version
        and stored.config_version == model.config_version
    ):
        return await with_visual_sources(session, stored)
    model = model.model_copy(update={
        "version": (stored.version + 1) if stored else 1,
        "changes_since_previous": changes,
    })
    snapshot = PortraitSnapshot(user_id=user.id, payload={})
    session.add(snapshot)
    await session.flush()
    model = model.model_copy(update={"snapshot_id": str(snapshot.id)})
    snapshot.payload = model.model_dump(mode="json")
    await session.commit()
    return await with_visual_sources(session, model)


async def get_portrait_history(session: AsyncSession, user: CurrentUser) -> list[PortraitModel]:
    rows = await session.execute(
        select(PortraitSnapshot).where(PortraitSnapshot.user_id == user.id)
        .order_by(PortraitSnapshot.created_at.desc()).limit(30)
    )
    models = [model for row in rows.scalars().all() if (model := _stored_model(row)) is not None]
    return [await with_visual_sources(session, model) for model in models]


async def get_portrait_snapshot(session: AsyncSession, user: CurrentUser, snapshot_id: UUID) -> PortraitModel | None:
    snapshot = await session.scalar(select(PortraitSnapshot).where(
        PortraitSnapshot.id == snapshot_id, PortraitSnapshot.user_id == user.id
    ))
    model = _stored_model(snapshot) if snapshot else None
    return await with_visual_sources(session, model) if model else None
