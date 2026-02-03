"""Compatibility shim for unpickling legacy sklearn pipelines.

Some trained joblib artifacts reference a module named `validators` that contains
custom transformers/validators (e.g. `FeatureOrderValidator`). In this codebase
we don't need those objects at runtime for inference, but joblib/pickle needs
to be able to import them to unpickle the pipeline.

This module provides minimal no-op implementations to satisfy unpickling.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

import numpy as np


class FeatureOrderValidator:
    """No-op transformer used only to satisfy pickle imports.

    The original training pipeline likely used this to enforce feature ordering
    by name. Our inference path uses ordered numeric arrays, so this is safe as
    a pass-through.
    """

    def __init__(self, feature_names: Optional[Iterable[str]] = None, **kwargs: Any):
        self.feature_names = list(feature_names) if feature_names is not None else None
        self.kwargs = dict(kwargs)

    def fit(self, X: Any, y: Any = None):
        return self

    def transform(self, X: Any):
        return X

    def fit_transform(self, X: Any, y: Any = None):
        return self.transform(X)

    # scikit-learn compatibility
    def get_feature_names_out(self, input_features: Any = None):
        if self.feature_names is not None:
            return np.asarray(self.feature_names)
        if input_features is None:
            return np.asarray([])
        try:
            return np.asarray(list(input_features))
        except Exception:
            return np.asarray([])
