"""Thin scorer: numeric features in, probabilities out; no retrieval or policy stages."""

import hashlib
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

import lightgbm as lgb
import numpy as np

from concord.c3_contracts import MODEL_VERSION, ScoredCandidate
from concord.features.reference import FEATURE_NAMES, REFERENCE_SCHEMA
from concord.metadata import content_sha256, require_sha256


class Scorer(Protocol):
    def fit(self, X: np.ndarray, y: np.ndarray) -> "Scorer": ...
    def predict_proba(self, X: np.ndarray) -> np.ndarray: ...
    def get_params(self) -> dict: ...
    def fingerprint(self) -> str: ...


def score_features(rows, candidates, scorer: Scorer, *, model_version: str = MODEL_VERSION) -> tuple[ScoredCandidate, ...]:
    from concord.features.reference import feature_matrix

    sources = {(c.s1_id, c.target_id): c.target_source for c in candidates}
    if len(sources) != len(candidates) or set(sources) != {(r.s1_id, r.target_id) for r in rows}:
        raise ValueError("scoring consumes exactly the bounded feature/candidate graph")
    values = scorer.predict_proba(feature_matrix(rows))
    if np.shape(values) != (len(rows),):
        raise ValueError("scorer must emit one probability per row")
    return tuple(ScoredCandidate(r.s1_id, r.target_id, sources[r.s1_id, r.target_id], float(p), scorer.fingerprint(), model_version)
                 for r, p in zip(rows, values, strict=True))


@dataclass(frozen=True, slots=True)
class ModelConfig:
    n_estimators: int = 600
    learning_rate: float = .05
    num_leaves: int = 63
    min_child_samples: int = 100
    reg_lambda: float = 1.
    subsample: float = 1.
    colsample_bytree: float = 1.
    random_state: int = 42
    seed_policy: str = "concord.fixed-seed-42.v1"
    n_jobs: int = 1
    deterministic: bool = True
    force_col_wise: bool = True

    def __post_init__(self):
        if any(type(v) is not int for v in (self.n_estimators, self.num_leaves, self.min_child_samples, self.random_state)):
            raise ValueError("tree, leaf, sample and seed parameters must be integers")
        if any(type(v) not in (float, int) for v in (self.learning_rate, self.reg_lambda, self.subsample, self.colsample_bytree)):
            raise ValueError("model numeric parameters cannot be bools or strings")
        fixed = (self.n_estimators, self.learning_rate, self.num_leaves, self.min_child_samples,
                 self.reg_lambda, self.subsample, self.colsample_bytree, self.random_state)
        if fixed != (600, .05, 63, 100, 1., 1., 1., 42):
            raise ValueError("reference model parameters are frozen")
        if self.seed_policy != "concord.fixed-seed-42.v1":
            raise ValueError("reference seed policy must be declared")
        if type(self.n_jobs) is not int or self.n_jobs < 1 or self.deterministic is not True or self.force_col_wise is not True:
            raise ValueError("explicit deterministic local threading required")

    @property
    def sha256(self):
        return content_sha256(asdict(self))


def _matrix(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float32)
    if X.ndim != 2 or X.shape[1] != 59 or not np.isfinite(X).all():
        raise ValueError("scorer needs a finite 59-column matrix")
    return X


class LightGBMScorer:
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.booster: lgb.Booster | None = None

    def get_params(self) -> dict:
        values = asdict(self.config)
        values.pop("seed_policy")
        return values | {"objective": "binary", "metric": "binary_logloss"}

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LightGBMScorer":
        X = _matrix(X)
        y = np.asarray(y)
        if y.shape != (len(X),) or set(y.tolist()) != {0, 1}:
            raise ValueError("training requires both binary classes and one label per row")
        model = lgb.LGBMClassifier(**self.get_params())
        model.fit(X, y, feature_name=list(FEATURE_NAMES))
        self.booster = model.booster_
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = _matrix(X)
        if self.booster is None:
            raise ValueError("scorer is not fitted")
        if not len(X):
            return np.empty(0, dtype=np.float64)
        scores = np.asarray(self.booster.predict(X, num_threads=self.config.n_jobs), dtype=np.float64)
        if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
            raise ValueError("invalid model probabilities")
        return scores

    def model_bytes(self) -> bytes:
        if self.booster is None:
            raise ValueError("scorer is not fitted")
        return self.booster.model_to_string().encode("utf-8")

    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_bytes()).hexdigest()

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.model_bytes())

    @classmethod
    def load(cls, path: str | Path, metadata: dict) -> "LightGBMScorer":
        if metadata["feature_schema_sha256"] != REFERENCE_SCHEMA.sha256:
            raise ValueError("model feature-schema mismatch")
        if metadata["format_version"] != "concord.lightgbm-text.v1":
            raise ValueError("unsupported model format")
        payload = Path(path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != metadata["model_sha256"]:
            raise ValueError("model artifact hash mismatch")
        fields = dict(metadata)
        identity = fields.pop("model_identity_sha256")
        require_sha256(identity)
        if content_sha256(fields) != identity:
            raise ValueError("model metadata identity mismatch")
        if metadata["lightgbm_version"] != version("lightgbm"):
            raise ValueError("model library-version mismatch")
        config = ModelConfig(**metadata["training_configuration"])
        if config.sha256 != metadata["training_config_sha256"]:
            raise ValueError("model training config mismatch")
        scorer = cls(config)
        scorer.booster = lgb.Booster(model_str=payload.decode("utf-8"))
        if scorer.booster.feature_name() != list(FEATURE_NAMES):
            raise ValueError("model feature order mismatch")
        return scorer


def model_metadata(scorer: LightGBMScorer, dataset_sha: str, split_sha: str,
                   plan_sha: str, negative_sha: str, training_pairs_sha: str,
                   feature_artifact_sha: str, retrieval_sha: str) -> dict:
    for digest in (dataset_sha, split_sha, plan_sha, negative_sha, training_pairs_sha,
                   feature_artifact_sha, retrieval_sha):
        require_sha256(digest)
    metadata = {
        "format_version": "concord.lightgbm-text.v1", "model_sha256": scorer.fingerprint(),
        "training_configuration": asdict(scorer.config), "training_config_sha256": scorer.config.sha256,
        "feature_schema_sha256": REFERENCE_SCHEMA.sha256, "dataset_fingerprint": dataset_sha,
        "split_fingerprint": split_sha, "split_plan_sha256": plan_sha,
        "negative_config_sha256": negative_sha, "training_pairs_sha256": training_pairs_sha,
        "feature_artifact_sha256": feature_artifact_sha, "retrieval_config_sha256": retrieval_sha,
        "lightgbm_version": version("lightgbm"), "numpy_version": version("numpy"),
        "actual_tree_count": scorer.booster.num_trees(),
    }
    metadata["model_identity_sha256"] = content_sha256(metadata)
    return metadata
