import numpy as np
import xgboost as xgb
import shap
from sklearn.ensemble import IsolationForest
from app.agents.state import AgentState

FEATURE_NAMES = ["price_change_pct", "volatility", "five_day_range_pct", "sentiment_score", "momentum_numeric"]

# Only a confidently high probability sets a hard fraud flag. Anything in
# the gray zone, or disagreement between the two models, routes to human
# review instead of the pipeline silently guessing either way.
FRAUD_THRESHOLD = 0.65
REVIEW_BAND_LOW = 0.35
REVIEW_BAND_HIGH = 0.65


def extract_fraud_features(state: dict) -> list[float]:
    """Turn already-computed upstream agent state into a fixed-order feature vector."""
    indicators = state.get("technical_indicators") or {}
    sentiment_score = state.get("sentiment_score")

    momentum_map = {"up": 1.0, "down": -1.0, "flat": 0.0}
    momentum_numeric = momentum_map.get(indicators.get("momentum"), 0.0)

    return [
        indicators.get("price_change_pct") or 0.0,
        indicators.get("volatility") or 0.0,
        indicators.get("five_day_range_pct") or 0.0,
        sentiment_score if sentiment_score is not None else 0.0,
        momentum_numeric,
    ]


def _generate_synthetic_training_data(n_samples: int = 600, anomaly_ratio: float = 0.12, seed: int = 42):
    """Build a labeled training set matching our real feature semantics.

    v2: widened the "normal" volatility/range distributions after seeing
    real AAPL data land close to the original boundary on a genuinely
    newsy-but-not-fraudulent week - v1 assumed real markets stay quieter
    than they actually do.
    """
    rng = np.random.default_rng(seed)
    n_anomaly = int(n_samples * anomaly_ratio)
    n_normal = n_samples - n_anomaly

    normal_change = rng.normal(0, 1.5, n_normal)
    normal_volatility = np.clip(rng.normal(2.0, 1.0, n_normal), 0, None)
    normal_range = np.clip(rng.normal(4.0, 2.0, n_normal), 0, None)
    normal_sentiment = np.clip(rng.normal(0, 0.3, n_normal), -1, 1)
    normal_momentum = np.where(normal_change > 0.3, 1.0, np.where(normal_change < -0.3, -1.0, 0.0))
    X_normal = np.column_stack([normal_change, normal_volatility, normal_range, normal_sentiment, normal_momentum])
    y_normal = np.zeros(n_normal)

    direction = rng.choice([1, -1], size=n_anomaly)
    magnitude = rng.uniform(8, 20, n_anomaly)
    anomaly_change = direction * magnitude
    anomaly_volatility = np.clip(rng.normal(6, 2, n_anomaly), 0, None)
    anomaly_range = np.clip(rng.normal(12, 4, n_anomaly), 0, None)
    anomaly_sentiment = np.clip(direction * rng.normal(0.7, 0.2, n_anomaly), -1, 1)
    anomaly_momentum = direction.astype(float)
    X_anomaly = np.column_stack([anomaly_change, anomaly_volatility, anomaly_range, anomaly_sentiment, anomaly_momentum])
    y_anomaly = np.ones(n_anomaly)

    X = np.vstack([X_normal, X_anomaly])
    y = np.concatenate([y_normal, y_anomaly])

    shuffle_idx = rng.permutation(len(y))
    return X[shuffle_idx], y[shuffle_idx]


_X_train, _y_train = _generate_synthetic_training_data()

_xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, eval_metric="logloss")
_xgb_model.fit(_X_train, _y_train)

_iso_forest = IsolationForest(contamination=0.12, random_state=42)
_iso_forest.fit(_X_train)

_shap_explainer = shap.TreeExplainer(_xgb_model)


def score_fraud(state: dict) -> dict:
    """Score a single case for fraud/anomaly signals using both models.

    Three real outcomes instead of one boolean:
    - fraud_flag=True: XGBoost is confidently over FRAUD_THRESHOLD
    - requires_human_review=True: confident fraud, a gray-zone probability,
      or the two models disagreeing - all genuinely need a person, not a
      silent auto-decision
    - neither flag: confidently clean
    """
    features = extract_fraud_features(state)
    X = np.array([features])

    fraud_probability = float(_xgb_model.predict_proba(X)[0, 1])
    is_isolation_anomaly = bool(_iso_forest.predict(X)[0] == -1)

    shap_values = _shap_explainer.shap_values(X)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    shap_explanation = {
        name: round(float(value), 3)
        for name, value in zip(FEATURE_NAMES, shap_values[0])
    }

    fraud_flag = fraud_probability > FRAUD_THRESHOLD
    models_disagree = is_isolation_anomaly != (fraud_probability > 0.5)
    in_gray_zone = REVIEW_BAND_LOW <= fraud_probability <= REVIEW_BAND_HIGH
    requires_human_review = fraud_flag or in_gray_zone or models_disagree

    return {
        "fraud_flag": fraud_flag,
        "fraud_confidence": round(fraud_probability, 3),
        "isolation_forest_flag": is_isolation_anomaly,
        "requires_human_review": requires_human_review,
        "shap_explanation": shap_explanation,
        "features_used": dict(zip(FEATURE_NAMES, features)),
    }

def fraud_detection_node(state: AgentState) -> dict:
    """LangGraph node: Fraud Detection Agent."""
    symbol = state["symbol"]

    if state.get("technical_indicators") is None or state.get("sentiment_score") is None:
        return {
            "agent_log": [f"[FraudDetection] Skipped - missing upstream data for {symbol}"],
        }

    result = score_fraud(state)

    log_line = (
        f"[FraudDetection] {symbol}: fraud_flag={result['fraud_flag']}, "
        f"confidence={result['fraud_confidence']}, "
        f"isolation_forest={result['isolation_forest_flag']}, "
        f"human_review={result['requires_human_review']}"
    )

    return {
        "fraud_flag": result["fraud_flag"],
        "fraud_confidence": result["fraud_confidence"],
        "shap_explanation": result["shap_explanation"],
        "requires_human_review": result["requires_human_review"],
        "agent_log": [log_line],
    }