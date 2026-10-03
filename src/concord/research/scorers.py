"""C4 numeric scorers; preprocessing is fitted on training rows only."""

from dataclasses import asdict
from importlib.metadata import version

import lightgbm as lgb
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from concord.features.reference import FEATURE_NAMES, FEATURE_SCHEMA_SHA256
from concord.metadata import content_sha256
from concord.modeling.scorer import LightGBMScorer
from concord.research.definitions import ExperimentDefinition


class ResearchScorer:
    def __init__(self, definition: ExperimentDefinition):
        self.definition = definition
        self.reference = None
        self.scaler = None
        self.logistic = None
        self.payload = None
        self._fingerprint = None

    def fit(self, X, y):
        X = self.definition.matrix(X)
        y = np.asarray(y)
        if set(y.tolist()) != {0, 1} or y.shape != (len(X),):
            raise ValueError("both training classes required")
        if self.definition.scorer == "lightgbm":
            self.reference = LightGBMScorer().fit(X, y)
            fitted = {"model_text": self.reference.model_bytes().decode("utf-8"),
                      "configuration": self.reference.get_params()}
        else:
            self.scaler = StandardScaler().fit(X)
            self.logistic = LogisticRegression(C=1., solver="liblinear", random_state=self.definition.seed,
                                               max_iter=2000, tol=1e-8).fit(self.scaler.transform(X), y)
            if np.any(self.logistic.n_iter_ >= 2000):
                raise ValueError("logistic challenger did not converge")
            fitted = {"mean": self.scaler.mean_.tolist(), "scale": self.scaler.scale_.tolist(),
                      "coefficient": self.logistic.coef_[0].tolist(), "intercept": float(self.logistic.intercept_[0]),
                      "configuration": self.logistic.get_params()}
        self.payload = {"schema_version": "concord.c4.numeric-model.v1", "definition": asdict(self.definition),
                        "definition_sha256": self.definition.sha256, "feature_schema_sha256": FEATURE_SCHEMA_SHA256,
                        "libraries": {n: version(n) for n in ("lightgbm", "scikit-learn", "numpy")},
                        "fitted": fitted}
        self._fingerprint = content_sha256(self.payload)
        return self

    def predict_proba(self, X):
        X = self.definition.matrix(X)
        if self.payload is None:
            raise ValueError("scorer is not fitted")
        if not len(X):
            return np.empty(0)
        if self.reference is not None:
            return self.reference.predict_proba(X)
        fitted = self.payload["fitted"]
        # Match StandardScaler's float32 in-place transform used at fit time.
        X -= np.array(fitted["mean"], dtype=X.dtype)
        X /= np.array(fitted["scale"], dtype=X.dtype)
        z = X @ np.array(fitted["coefficient"]) + fitted["intercept"]
        # Stable sigmoid without an overflow on extreme finite inputs.
        return np.exp(-np.logaddexp(0., -z))

    def get_params(self):
        return asdict(self.definition)

    def fingerprint(self):
        if self.payload is None:
            raise ValueError("scorer is not fitted")
        return self._fingerprint

    @classmethod
    def load(cls, payload):
        if payload["schema_version"] != "concord.c4.numeric-model.v1" or payload["feature_schema_sha256"] != FEATURE_SCHEMA_SHA256:
            raise ValueError("C4 model schema mismatch")
        scorer = cls(ExperimentDefinition(**payload["definition"]))
        if scorer.definition.sha256 != payload["definition_sha256"]:
            raise ValueError("C4 model definition mismatch")
        if payload["libraries"] != {n: version(n) for n in ("lightgbm", "scikit-learn", "numpy")}:
            raise ValueError("C4 model environment mismatch")
        scorer.payload = payload
        scorer._fingerprint = content_sha256(payload)
        if scorer.definition.scorer == "lightgbm":
            scorer.reference = LightGBMScorer()
            scorer.reference.booster = lgb.Booster(model_str=payload["fitted"]["model_text"])
            if scorer.reference.booster.feature_name() != list(FEATURE_NAMES):
                raise ValueError("C4 model feature order mismatch")
        return scorer
