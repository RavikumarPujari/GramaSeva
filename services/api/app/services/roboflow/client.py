import os
import logging
from typing import Optional
from inference_sdk import InferenceHTTPClient, InferenceConfiguration
from app.core.config import settings

logger = logging.getLogger(__name__)

class RoboflowClientManager:
    """
    Singleton manager for authenticated Roboflow InferenceHTTPClient.
    Uses header-based API key transport as required by Roboflow Serverless Inference.
    Guarantees API keys are never logged, leaked, or exposed in exceptions.
    """
    _instance: Optional["RoboflowClientManager"] = None
    _client: Optional[InferenceHTTPClient] = None
    _cached_api_key: Optional[str] = None
    _cached_api_url: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RoboflowClientManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_api_key(cls) -> str:
        """Reads API key strictly from environment/settings without logging."""
        key = (settings.roboflow_api_key or os.environ.get("ROBOFLOW_API_KEY", "")).strip()
        return key

    @classmethod
    def get_api_url(cls) -> str:
        """Returns the configured Roboflow serverless endpoint."""
        url = settings.roboflow_api_url or os.environ.get("ROBOFLOW_API_URL", "https://serverless.roboflow.com")
        return url.rstrip("/")

    @classmethod
    def is_configured(cls) -> bool:
        """Checks if a valid, non-placeholder API key is configured."""
        key = cls.get_api_key()
        return bool(key and key != "YOUR_NEW_PRIVATE_KEY" and len(key) >= 8)

    @classmethod
    def get_client(cls) -> Optional[InferenceHTTPClient]:
        """
        Returns a cached, re-usable InferenceHTTPClient instance configured
        with header-based authentication.
        """
        api_key = cls.get_api_key()
        api_url = cls.get_api_url()

        if not api_key or api_key == "YOUR_NEW_PRIVATE_KEY":
            return None

        if cls._client is not None and cls._cached_api_key == api_key and cls._cached_api_url == api_url:
            return cls._client

        try:
            client = InferenceHTTPClient(
                api_url=api_url,
                api_key=api_key,
            ).configure(
                InferenceConfiguration(
                    api_key_transport="header"
                )
            )
            cls._client = client
            cls._cached_api_key = api_key
            cls._cached_api_url = api_url
            return cls._client
        except Exception as e:
            logger.warning("Could not initialize Roboflow InferenceHTTPClient: %s", type(e).__name__)
            return None
