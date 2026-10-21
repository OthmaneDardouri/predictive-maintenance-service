from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests by method, route template and status code.",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency by method and route template.",
    ["method", "path"],
)
MODEL_LOADED = Gauge("model_loaded", "1 if a model is loaded, 0 otherwise.")
PREDICTIONS = Counter(
    "predictions_total", "Predictions served, by predicted class.", ["prediction"]
)
FAILURE_PROBABILITY = Histogram(
    "prediction_failure_probability",
    "Distribution of predicted failure probabilities.",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
# One input feature, to compare against the training distribution (mean 40, std 10).
INPUT_TORQUE = Histogram(
    "model_input_torque_nm",
    "Distribution of the torque input.",
    buckets=(10, 20, 30, 40, 50, 60, 70, 80, 100),
)
