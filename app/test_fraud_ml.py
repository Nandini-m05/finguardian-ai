import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import IsolationForest
import xgboost as xgb
import shap

# Small synthetic dataset - 200 samples, 5 features, ~10% "positive" class
# to mimic how rare real fraud/anomaly patterns tend to be.
X, y = make_classification(
    n_samples=200,
    n_features=5,
    n_informative=3,
    n_redundant=0,
    weights=[0.9, 0.1],
    random_state=42,
)
feature_names = ["volume_zscore", "price_deviation", "trade_frequency", "size_anomaly", "time_gap"]

# 1. XGBoost - supervised classifier
model = xgb.XGBClassifier(n_estimators=50, max_depth=3, eval_metric="logloss")
model.fit(X, y)
predictions = model.predict_proba(X)[:, 1]
print("XGBoost trained. Sample fraud probabilities:", predictions[:5].round(3))

# 2. Isolation Forest - unsupervised anomaly detector, no labels used at all
iso_forest = IsolationForest(contamination=0.1, random_state=42)
iso_forest.fit(X)
anomaly_scores = iso_forest.decision_function(X)
print("\nIsolation Forest trained. Sample anomaly scores:", anomaly_scores[:5].round(3))

# 3. SHAP - explain one XGBoost prediction, feature by feature
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X[:1])
# Different shap versions return this shaped differently for binary
# classification - handle both so a version quirk doesn't crash this test.
if isinstance(shap_values, list):
    shap_values = shap_values[1]  # class 1 = "fraud"

print("\nSHAP explanation for sample 0:")
for name, value in zip(feature_names, shap_values[0]):
    print(f"  {name}: {value:+.3f}")