
import json
from functools import lru_cache

import faiss
import joblib
from app.core.onnx_embedding import ONNXEmbeddingModel

from app.core.config import (
    RESUMES_FILE,
    JOBS_FILE,
    FAISS_INDEX_FILE,
    RANDOM_FOREST_FILE,
    FEATURE_COLUMNS_FILE,
    KMEANS_FILE,
    IMPUTATION_VALUES_FILE,
    SKILL_NORMALIZATION_FILE,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    EXPECTED_FEATURE_COUNT,
    EXPECTED_KMEANS_CLUSTERS,
    EXPECTED_FAISS_VECTORS,
)


def _load_artifact(path):
    """Load a Joblib/Pickle deployment artifact."""
    return joblib.load(path)


def _load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def get_model_bundle():

    artifact_paths = {
        "resumes": RESUMES_FILE,
        "jobs": JOBS_FILE,
        "faiss_index": FAISS_INDEX_FILE,
        "random_forest": RANDOM_FOREST_FILE,
        "feature_columns": FEATURE_COLUMNS_FILE,
        "kmeans": KMEANS_FILE,
        "imputation_values": IMPUTATION_VALUES_FILE,
        "skill_normalization": SKILL_NORMALIZATION_FILE,
    }

    missing = [
        name
        for name, path in artifact_paths.items()
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing deployment artifacts: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    resumes = _load_json(RESUMES_FILE)
    jobs = _load_json(JOBS_FILE)

    # --------------------------------------------------------
    # FAISS
    # --------------------------------------------------------

    faiss_index = faiss.read_index(
        str(FAISS_INDEX_FILE)
    )

    # --------------------------------------------------------
    # Joblib artifacts
    # --------------------------------------------------------

    random_forest_model = _load_artifact(
        RANDOM_FOREST_FILE
    )

    feature_columns = _load_artifact(
        FEATURE_COLUMNS_FILE
    )

    kmeans_model = _load_artifact(
        KMEANS_FILE
    )

    imputation_values = _load_artifact(
        IMPUTATION_VALUES_FILE
    )

    skill_normalization = _load_artifact(
        SKILL_NORMALIZATION_FILE
    )

    # --------------------------------------------------------
    # Embedding model
    # --------------------------------------------------------

    embedding_model = ONNXEmbeddingModel()

    # --------------------------------------------------------
    # Artifact validation
    # --------------------------------------------------------

    if len(feature_columns) != EXPECTED_FEATURE_COUNT:
        raise ValueError(
            "Unexpected feature count: "
            f"{len(feature_columns)}; "
            f"expected {EXPECTED_FEATURE_COUNT}"
        )

    if faiss_index.d != EMBEDDING_DIMENSION:
        raise ValueError(
            "Unexpected FAISS dimension: "
            f"{faiss_index.d}; "
            f"expected {EMBEDDING_DIMENSION}"
        )

    if faiss_index.ntotal != EXPECTED_FAISS_VECTORS:
        raise ValueError(
            "Unexpected FAISS vector count: "
            f"{faiss_index.ntotal}; "
            f"expected {EXPECTED_FAISS_VECTORS}"
        )

    if getattr(kmeans_model, "n_clusters", None) != (
        EXPECTED_KMEANS_CLUSTERS
    ):
        raise ValueError(
            "Unexpected KMeans cluster count: "
            f"{getattr(kmeans_model, 'n_clusters', None)}; "
            f"expected {EXPECTED_KMEANS_CLUSTERS}"
        )

    embedding_dimension = (
        embedding_model.get_sentence_embedding_dimension()
    )

    if embedding_dimension != EMBEDDING_DIMENSION:
        raise ValueError(
            "Unexpected embedding dimension: "
            f"{embedding_dimension}; "
            f"expected {EMBEDDING_DIMENSION}"
        )

    return {
        "resumes": resumes,
        "jobs": jobs,
        "faiss_index": faiss_index,
        "random_forest_model": random_forest_model,
        "feature_columns": feature_columns,
        "kmeans_model": kmeans_model,
        "imputation_values": imputation_values,
        "skill_normalization": skill_normalization,
        "embedding_model": embedding_model,
    }
