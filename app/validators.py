"""Compatibility shim for older joblib artifacts.

Some previously trained pipelines were serialized with a custom transformer
named ``validators.FeatureOrderValidator``. At runtime we want that class to
be importable so unpickling succeeds, but we do not depend on the third-party
`validators` PyPI package.
"""

from __future__ import annotations


class FeatureOrderValidator:  # pragma: no cover
    """No-op sklearn-compatible transformer.

    This exists only so joblib can import it during unpickling.
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X
