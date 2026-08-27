from transformers import pipeline

# First run downloads the model (~400MB) and caches it locally.
# Subsequent runs load instantly from cache.
classifier = pipeline("sentiment-analysis", model="ProsusAI/finbert")

test_headlines = [
    "Apple shares surge after record iPhone sales beat analyst expectations",
    "Company shares plunge amid fraud investigation and executive resignations",
    "Quarterly earnings came in roughly in line with market forecasts",
]

for headline in test_headlines:
    result = classifier(headline)[0]
    print(f"{result['label']:10s} ({result['score']:.2f})  {headline}")