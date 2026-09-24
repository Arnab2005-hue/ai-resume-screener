from pathlib import Path


# ------------------------------------------------------------
# Project paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BACKEND_ROOT = PROJECT_ROOT / "backend"
APP_ROOT = BACKEND_ROOT / "app"
DEPLOYMENT_ROOT = PROJECT_ROOT / "deployment"


# ------------------------------------------------------------
# Deployment artifacts
# ------------------------------------------------------------

RESUMES_FILE = DEPLOYMENT_ROOT / "resumes.json"
JOBS_FILE = DEPLOYMENT_ROOT / "jobs.json"
FAISS_INDEX_FILE = DEPLOYMENT_ROOT / "resume_index.faiss"

RANDOM_FOREST_FILE = (
    DEPLOYMENT_ROOT / "random_forest_model.pkl"
)

FEATURE_COLUMNS_FILE = (
    DEPLOYMENT_ROOT / "feature_columns.pkl"
)

KMEANS_FILE = (
    DEPLOYMENT_ROOT / "kmeans_model.pkl"
)

IMPUTATION_VALUES_FILE = (
    DEPLOYMENT_ROOT / "imputation_values.pkl"
)

SKILL_NORMALIZATION_FILE = (
    DEPLOYMENT_ROOT / "skill_normalization.pkl"
)


# ------------------------------------------------------------
# Model settings
# ------------------------------------------------------------

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

EMBEDDING_DIMENSION = 384

EXPECTED_FEATURE_COUNT = 11

EXPECTED_KMEANS_CLUSTERS = 6

EXPECTED_FAISS_VECTORS = 9544

MAX_BATCH_SIZE = 800

MAX_FILE_SIZE_MB = 10


# ------------------------------------------------------------
# Supported resume file types
# ------------------------------------------------------------

SUPPORTED_RESUME_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
}
