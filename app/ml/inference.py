"""ML Inference Engine.

Runs binary detection and (optionally) multiclass classification.

Design goals:
- Accept raw 70-length feature arrays (no named columns required).
- Support sklearn/joblib Pipelines that may include validation/scaling/PCA.
- Support multiclass models that operate on PCA components (e.g., 35 PCs).
"""

import logging
from typing import Any, Dict, Optional, Sequence

import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_pipeline_fitted(model) -> bool:
    """Best-effort check whether common pipeline steps are fitted.

    A few of the shipped artifacts can unpickle but contain an unfitted
    `StandardScaler`, which then fails at runtime with:
    "This StandardScaler instance is not fitted yet".
    """
    try:
        from sklearn.utils.validation import check_is_fitted

        named_steps = getattr(model, "named_steps", None)
        if not named_steps:
            return True

        scaler = named_steps.get("scaler")
        if scaler is not None:
            check_is_fitted(scaler)

        ipca = named_steps.get("ipca")
        if ipca is not None:
            check_is_fitted(ipca)

        return True
    except Exception:
        return False


class MLInference:
    """
    ML Inference Engine for network attack detection
    
    Flow:
    1. Binary model checks if attack exists
    2. If BENIGN -> return no attack
    3. If ATTACK -> run classification model
    4. If classification returns BENIGN -> mark as UNKNOWN
    """
    
    def __init__(self):
        """Initialize inference engine (models loaded separately)"""
        self.binary_model = None
        self.classification_model = None
        self.is_loaded = False
        logger.info("ML Inference engine initialized (models not loaded)")
    
    def load_models(self, binary_path: str, classification_path: str):
        """Load joblib models from disk.

        Both are expected to be sklearn estimators/pipelines. The multiclass model
        may expect either the raw 70 features or the PCA output of the binary pipeline.
        """
        try:
            import joblib

            binary_path_abs = str(Path(binary_path).expanduser().resolve())
            classification_path_abs = str(Path(classification_path).expanduser().resolve())

            logger.info("Loading ML models")
            logger.info("Binary model path: %s", binary_path_abs)
            logger.info("Multiclass model path: %s", classification_path_abs)

            self.binary_model = joblib.load(binary_path_abs)
            self.classification_model = joblib.load(classification_path_abs)

            binary_ok = _is_pipeline_fitted(self.binary_model)
            multiclass_ok = _is_pipeline_fitted(self.classification_model)
            if not binary_ok or not multiclass_ok:
                logger.error(
                    "One or more ML pipelines are not fitted (binary_ok=%s, multiclass_ok=%s). "
                    "Falling back to mock predictions.",
                    binary_ok,
                    multiclass_ok,
                )
                self.binary_model = None
                self.classification_model = None
                self.is_loaded = False
                return

            self.is_loaded = True
            
            logger.info("ML models loaded successfully")
            logger.info(f"Binary model: {type(self.binary_model).__name__}")
            logger.info(f"Classification model: {type(self.classification_model).__name__}")
            logger.info(
                "Classification classes: %s",
                getattr(self.classification_model, 'classes_', 'N/A')
            )
            
        except Exception:
            logger.exception("Failed to load models")
            self.is_loaded = False
            raise
    
    def _as_row(self, features: Sequence[float]) -> np.ndarray:
        arr = np.asarray(features, dtype=float)
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        return arr.reshape(1, -1)

    def _predict_proba_safe(self, model, X: np.ndarray) -> Optional[np.ndarray]:
        try:
            if hasattr(model, 'predict_proba'):
                return model.predict_proba(X)
        except Exception:
            return None
        return None

    def _transform_if_possible(self, model, X: np.ndarray) -> Optional[np.ndarray]:
        try:
            if hasattr(model, 'transform'):
                return model.transform(X)
        except Exception:
            return None
        return None

    def predict(self, features: Sequence[float]) -> Dict[str, Any]:
        """
        Run inference with binary → classification flow
        
        Flow:
        1. Binary model checks if attack exists
        2. If BENIGN -> return no attack
        3. If ATTACK -> run classification model
        4. If classification returns BENIGN -> mark as UNKNOWN
        
        Args:
            features: Preprocessed feature array (70 features)
            
        Returns:
            dict with prediction results
        """
        if not self.is_loaded:
            logger.warning("Models not loaded, returning mock prediction")
            out = self._mock_prediction()
            out['debug'] = {
                'models_loaded': False,
                'binary_model_type': None,
                'classification_model_type': None,
            }
            return out
        
        try:
            X_raw = self._as_row(features)

            debug = {
                'models_loaded': True,
                'binary_model_type': type(self.binary_model).__name__ if self.binary_model is not None else None,
                'classification_model_type': type(self.classification_model).__name__ if self.classification_model is not None else None,
            }

            # Step 1: Binary detection (expects 70 raw features)
            binary_pred = self.binary_model.predict(X_raw)[0]
            binary_proba_all = self._predict_proba_safe(self.binary_model, X_raw)
            binary_proba = binary_proba_all[0] if binary_proba_all is not None else None
            
            # If binary model says BENIGN, no attack detected
            if binary_pred == 0:  # 0 = BENIGN, 1 = ATTACK
                return {
                    'is_attack': False,
                    'attack_type': 'Normal',
                    'confidence': float(binary_proba[0]) if binary_proba is not None else 0.0,
                    'binary_confidence': float(binary_proba[0]) if binary_proba is not None else 0.0,
                    'classification_confidence': None,
                    'debug': debug,
                }
            
            # Step 2: Binary detected attack, run classification
            logger.info("Binary model detected attack, running classification...")

            # If multiclass model expects PCA features (35 PCs), use binary pipeline transform output.
            X_for_class = X_raw
            if self.classification_model is not None:
                try:
                    expected = getattr(self.classification_model, 'n_features_in_', None)
                except Exception:
                    expected = None

                if expected and expected != X_raw.shape[1]:
                    X_pca = self._transform_if_possible(self.binary_model, X_raw)
                    if X_pca is not None and X_pca.shape[1] == expected:
                        X_for_class = X_pca
                        debug['used_binary_transform_for_multiclass'] = True
                    else:
                        debug['used_binary_transform_for_multiclass'] = False
                else:
                    debug['used_binary_transform_for_multiclass'] = False

            class_pred = self.classification_model.predict(X_for_class)[0]
            class_proba_all = self._predict_proba_safe(self.classification_model, X_for_class)
            class_proba = class_proba_all[0] if class_proba_all is not None else None
            max_class_confidence = float(np.max(class_proba)) if class_proba is not None else 0.0

            # Get attack type name (prefer estimator's classes_)
            classes = getattr(self.classification_model, 'classes_', None)
            if classes is not None:
                try:
                    attack_type = str(classes[int(class_pred)])
                except Exception:
                    attack_type = str(class_pred)
            else:
                attack_type = str(class_pred)
            
            # Step 3: If classification returns BENIGN, treat as UNKNOWN
            if attack_type.upper() in ['BENIGN', 'NORMAL']:
                logger.warning("Classification returned BENIGN despite binary detection - marking as UNKNOWN")
                attack_type = 'UNKNOWN'
                if binary_proba is not None and len(binary_proba) > 1:
                    max_class_confidence = float(binary_proba[1])
            
            return {
                'is_attack': True,
                'attack_type': attack_type,
                'confidence': max_class_confidence,
                'binary_confidence': float(binary_proba[1]) if binary_proba is not None and len(binary_proba) > 1 else 0.0,
                'classification_confidence': float(np.max(class_proba)) if class_proba is not None else None,
                'debug': debug,
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise
    
    def _mock_prediction(self) -> Dict[str, Any]:
        """Return mock prediction for testing without models"""
        import random
        
        is_attack = random.choice([True, False])
        
        if not is_attack:
            return {
                'is_attack': False,
                'attack_type': 'Normal',
                'confidence': 0.95,
                'binary_confidence': 0.95,
                'classification_confidence': None
            }
        
        attack_types = ['Port Scan', 'DDoS', 'Brute Force', 'SQL Injection', 'XSS', 'UNKNOWN']
        attack_type = random.choice(attack_types)
        
        return {
            'is_attack': True,
            'attack_type': attack_type,
            'confidence': random.uniform(0.7, 0.95),
            'binary_confidence': random.uniform(0.8, 0.99),
            'classification_confidence': random.uniform(0.6, 0.9)
        }


# Global inference engine instance
_inference_engine = None


def get_inference_engine() -> MLInference:
    """Get global inference engine instance"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = MLInference()
    return _inference_engine
