from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    MAX_BATCH_SIZE,
    MAX_FILE_SIZE_MB,
)

from app.core.model_loader import get_model_bundle
from app.api.v1.endpoints.screening import router as screening_router


app = FastAPI(
    title="AI Resume Screening & Candidate Clustering API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(screening_router)


@app.get("/")
def root():
    return {
        "name": "AI Resume Screening & Candidate Clustering API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "resume-screening-api",
    }


@app.get("/api/v1/model-info")
def model_info():

    bundle = get_model_bundle()

    model = type(
        bundle["random_forest_model"]
    ).__name__

    feature_columns = list(
        bundle["feature_columns"]
    )

    kmeans_clusters = (
        bundle["kmeans_model"].n_clusters
    )

    faiss_vectors = (
        bundle["faiss_index"].ntotal
    )

    return {
        "model": model,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "kmeans_clusters": kmeans_clusters,
        "faiss_vectors": faiss_vectors,
        "resume_count": len(bundle["resumes"]),
        "job_count": len(bundle["jobs"]),
        "maximum_batch_size": MAX_BATCH_SIZE,
        "maximum_file_size_mb": MAX_FILE_SIZE_MB,
    }



# ============================================================
# DATABASE INTEGRATION
# ============================================================

from app.api.v1.endpoints.database import (
    router as database_router,
)

from app.database_middleware import (
    database_persistence_dispatch,
)


app.include_router(
    database_router
)


@app.middleware("http")
async def database_persistence_middleware(
    request,
    call_next,
):

    return await database_persistence_dispatch(
        request,
        call_next,
    )

