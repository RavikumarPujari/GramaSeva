import os
from inference_sdk import InferenceHTTPClient, InferenceConfiguration

models = [
    ("Model 1", "civic_issues_v1-dc7ae-zzdgj/1"),
    ("Model 2", "civic-issue-yljwt-tptzy/2"),
    ("Model 3", "civic-issues-qj5pb/2"),
]

api_url = "https://serverless.roboflow.com"
api_key = os.environ.get("ROBOFLOW_API_KEY", "YOUR_NEW_PRIVATE_KEY")

print(f"Testing connectivity to {api_url} for 3 models with key={api_key[:6]}...")

client = InferenceHTTPClient(
    api_url=api_url,
    api_key=api_key
).configure(InferenceConfiguration(
    api_key_transport="header"
))

test_image = "services/api/storage/private/originals/0b13997fbc2b4094ac1ed624d619f006.jpg"

for name, model_id in models:
    print(f"\n--- Probing {name}: {model_id} ---")
    try:
        res = client.infer(test_image, model_id=model_id)
        print(f"SUCCESS: {res}")
    except Exception as e:
        print(f"Response: {type(e).__name__}: {e}")
