from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyze_jobs import router as analyze_jobs_router
from app.api.finance_routes import router as finance_router
from app.api.interview_routes import router as interview_router
from app.api.market_routes import router as market_router
from app.api.news_routes import router as news_router
from app.api.routes import router
from app.core.config import settings
from app.db.session import init_db
from app.rag.providers import init_rag_providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    init_rag_providers(settings.bizrag_db_path)
    yield


app = FastAPI(
    title="나도사장 API",
    description="AI 기반 창업 사업성 분석 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(interview_router)
app.include_router(analyze_jobs_router)
app.include_router(finance_router)
app.include_router(market_router)
app.include_router(news_router)
