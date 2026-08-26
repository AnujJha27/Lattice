import uuid
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import Concept, Quiz, Review, UserConcept
from app.db.models.learning import MasteryState
from app.db.session import get_session

router = APIRouter(tags=["quizzes"])

class QuizOut(BaseModel):
    id: uuid.UUID
    question: str
    options: list[str]

class QuizAnswer(BaseModel):
    answer: int = Field(ge=0)
    response_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class GeneratedQuiz(BaseModel):
    question: str = Field(min_length=10, max_length=500)
    options: list[str] = Field(min_length=3, max_length=5)
    answer: int = Field(ge=0)
    rationale: str = Field(default="", max_length=1000)

@router.post("/concepts/{concept_id}/quiz", response_model=QuizOut)
async def create_quiz(concept_id: uuid.UUID, user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    concept = (await session.execute(select(Concept).where(Concept.id == concept_id))).scalar_one_or_none()
    if concept is None: raise NotFound("concept", concept_id)
    cached = (await session.execute(select(Quiz).where(
        Quiz.user_id == user.id, Quiz.concept_id == concept_id,
        Quiz.created_at >= datetime.now(UTC) - timedelta(hours=24),
    ).order_by(Quiz.created_at.desc()).limit(1))).scalar_one_or_none()
    if cached is not None:
        return QuizOut(id=cached.id, question=cached.question, options=cached.options)
    generated: GeneratedQuiz | None = None
    from app.core.config import get_settings
    settings = get_settings()
    if settings.google_api_key or (settings.openrouter_api_key and settings.openrouter_model):
        try:
            from app.providers.factory import get_llm_provider
            prompt = (
                "Create one rigorous multiple-choice question for this concept. "
                "Use exactly one correct answer, plausible distractors, and no trick wording.\n"
                f"Concept: {concept.canonical_name}\nDescription: {concept.description or 'No description available.'}"
            )
            response = await get_llm_provider().generate_structured(prompt, GeneratedQuiz.model_json_schema())
            candidate = GeneratedQuiz.model_validate(response.structured or {})
            if candidate.answer < len(candidate.options):
                generated = candidate
        except (ValidationError, ValueError, TypeError):
            generated = None
        except Exception:
            generated = None
    generated = generated or GeneratedQuiz(
        question=f"Which statement best describes {concept.canonical_name}?",
        options=[concept.description or f"A core idea in {concept.canonical_name}.", "An unrelated topic.", "None of the above."],
        answer=0,
        rationale=concept.description or "Review the lesson for the explanation.",
    )
    quiz = Quiz(user_id=user.id, concept_id=concept_id, question=generated.question,
                options=generated.options, answer=generated.answer, rationale=generated.rationale)
    session.add(quiz); await session.commit()
    return QuizOut(id=quiz.id, question=quiz.question, options=quiz.options)

@router.post("/quizzes/{quiz_id}/answer")
async def answer_quiz(quiz_id: uuid.UUID, payload: QuizAnswer, user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    quiz = (await session.execute(select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user.id))).scalar_one_or_none()
    if quiz is None: raise NotFound("quiz", quiz_id)
    if payload.answer >= len(quiz.options):
        return {"correct": False, "rationale": "Choose one of the listed options.", "next_review_at": None}
    correct = payload.answer == quiz.answer
    state = (await session.execute(select(UserConcept).where(UserConcept.user_id == user.id, UserConcept.concept_id == quiz.concept_id))).scalar_one_or_none()
    if state is not None:
        previous_mastery = float(state.mastery_score)
        state.attempt_count += 1
        state.review_count += 1
        state.successful_reviews = state.successful_reviews + 1 if correct else 0
        state.mastery_score = max(0, min(100, float(state.mastery_score) + (12 if correct else -8)))
        state.state = MasteryState.MASTERED if state.mastery_score >= 85 else MasteryState.FAMILIAR if state.mastery_score >= 60 else MasteryState.LEARNING
        state.last_tested_at = datetime.now(UTC)
        state.next_review_at = datetime.now(UTC) + timedelta(days=min(60, max(1, (1 + state.successful_reviews) * (2 if correct else 1))))
        session.add(Review(user_id=user.id, concept_id=quiz.concept_id, quiz_id=quiz.id,
                           correct=correct, confidence=3, previous_mastery=previous_mastery,
                           mastery_after=float(state.mastery_score), response_ms=payload.response_ms))
        await session.commit()
    return {"correct": correct, "rationale": quiz.rationale, "next_review_at": state.next_review_at if state else None}
