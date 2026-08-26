"""Model registry — single import surface for Alembic and the app."""
from app.db.base import Base
from app.db.models.concept import Concept, ConceptEdge
from app.db.models.job import Job
from app.db.models.learning import (
    Goal,
    GoalConcept,
    MasteryState,
    Pathway,
    PathwayConcept,
    PathwaySection,
    UserConcept,
)
from app.db.models.lesson import AIGeneration, Lesson, LessonSource, PromptVersion
from app.db.models.source import ConceptSource, Source, SourceChunk
from app.db.models.user import Profile
from app.db.models.quiz import Quiz
from app.db.models.review import Review
from app.db.models.recommendation import RecommendationEvent, RecommendationEventType
from app.db.models.portrait import PortraitFeedback, PortraitFeedbackKind, PortraitSnapshot

__all__ = [
    "Base",
    "Concept",
    "ConceptEdge",
    "Profile",
    "UserConcept",
    "MasteryState",
    "Goal",
    "GoalConcept",
    "Pathway",
    "PathwaySection",
    "PathwayConcept",
    "Source",
    "SourceChunk",
    "ConceptSource",
    "Lesson",
    "LessonSource",
    "PromptVersion",
    "AIGeneration",
    "Job",
    "Quiz",
    "Review",
    "RecommendationEvent",
    "RecommendationEventType",
    "PortraitSnapshot",
    "PortraitFeedback",
    "PortraitFeedbackKind",
]
