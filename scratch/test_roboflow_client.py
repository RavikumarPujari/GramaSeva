import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("ROBOFLOW_API_KEY", "")
model_id = os.environ.get("ROBOFLOW_MODEL_ID", "civic_issues_v1-dc7ae-zzdgj/1")
api_url = os.environ.get("ROBOFLOW_API_URL", "https://serverless.roboflow.com")

print(f"Model ID: {model_id}")
print(f"API URL: {api_url}")
print(f"API Key present: {bool(api_key and api_key != 'YOUR_NEW_PRIVATE_KEY')}")

from inference_sdk import InferenceHTTPClient, InferenceConfiguration

client = InferenceHTTPClient(
    api_url=api_url,
    api_key=api_key,
).configure(InferenceConfiguration(
    api_key_transport="header"
))

image_path = "services/api/storage/private/originals/0b13997fbc2b4094ac1ed624d619f006.jpg"
try:
    result = client.infer(image_path, model_id=model_id)
    print("Inference success! Result keys:", list(result.keys()) if isinstance(result, dict) else type(result))
    print("Predictions count:", len(result.get("predictions", [])) if isinstance(result, dict) else "N/A")
except Exception as e:
    print(f"Inference caught expected/actual error: {type(e).__name__}: {e}")
