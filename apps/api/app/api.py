"""Route aggregation — one place to see every exposed domain."""
from fastapi import APIRouter

from app.modules.brain.routes import router as brain_router
from app.modules.concepts.routes import router as concepts_router
from app.modules.discovery.routes import router as discovery_router
from app.modules.health.routes import router as health_router
from app.modules.lessons.routes import router as lessons_router
from app.modules.pathways.routes import router as pathways_router
from app.modules.portrait.routes import router as portrait_router
from app.modules.quizzes.routes import router as quizzes_router
from app.modules.recommendations.routes import router as recommendations_router
from app.modules.retrieval.routes import router as retrieval_router
from app.modules.reviews.routes import router as reviews_router
from app.modules.sources.routes import router as sources_router
from app.modules.users.routes import router as users_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(brain_router)
api_router.include_router(concepts_router)
api_router.include_router(pathways_router)
api_router.include_router(lessons_router)
api_router.include_router(sources_router)
api_router.include_router(retrieval_router)
api_router.include_router(reviews_router)
api_router.include_router(recommendations_router)
api_router.include_router(quizzes_router)
api_router.include_router(discovery_router)
api_router.include_router(portrait_router)
