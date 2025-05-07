from abc import ABC, abstractmethod
import requests
import json

class AuthStrategy(ABC):
    @abstractmethod
    def prepare_session(self, session: requests.Session, url: str, **kwargs) -> requests.Session:
        """Prepares the requests session with necessary auth headers or cookies."""
        pass

    @abstractmethod
    def get_headers(self, **kwargs) -> dict:
        """Returns headers required for direct API/WebSocket connections."""
        pass

    @abstractmethod
    def get_target_url(self, initial_url: str, **kwargs) -> str:
        """
        Returns the actual Jupyter server URL.
        For simple cases, this is initial_url. For others (e.g. SageMaker presigned),
        it might involve an intermediate step.
        """
        return initial_url

class TokenAuthStrategy(AuthStrategy):
    def __init__(self, secret: str):
        self.secret = secret # Store for DumbConnection to potentially access
        self._headers = {"Authorization": f"token {self.secret}"}

    def prepare_session(self, session: requests.Session, url: str, **kwargs) -> requests.Session:
        session.headers.update(self._headers)
        return session

    def get_headers(self, **kwargs) -> dict:
        return self._headers

class JupyterHubAuthStrategy(AuthStrategy):
    def __init__(self, hub_url: str, api_token: str, console_print_callback=None):
        self.hub_url = hub_url.rstrip('/')
        self.api_token = api_token
        self._headers = {"Authorization": f"token {self.api_token}"}
        self.resolved_target_url = "" # This will be hub_url/user/username/
        self.username = None
        self.print_func = console_print_callback or print # For logging/errors from strategy

        self._resolve_user_server()

    def _resolve_user_server(self):
        """Tries to get the username and construct the user server URL."""
        if not self.hub_url or not self.api_token:
            self.print_func("[JupyterHubAuth] Hub URL or API token is missing.", category="Error")
            return

        user_api_url = f"{self.hub_url}/hub/api/user"
        try:
            self.print_func(f"[JupyterHubAuth] Attempting to get user info from {user_api_url}", category="Info")
            response = requests.get(user_api_url, headers=self._headers, timeout=10)
            response.raise_for_status() # Raise an exception for HTTP error codes
            user_data = response.json()
            self.username = user_data.get("name")
            if self.username:
                self.resolved_target_url = f"{self.hub_url}/user/{self.username}/"
                self.print_func(f"[JupyterHubAuth] Resolved user server URL to: {self.resolved_target_url}", category="Info")
            else:
                self.print_func("[JupyterHubAuth] Could not determine username from Hub API response.", category="Error")
                self.print_func(f"[JupyterHubAuth] Response Data: {user_data}", category="Debug")

        except requests.exceptions.HTTPError as e:
            self.print_func(f"[JupyterHubAuth] HTTP error resolving user server: {e}", category="Error")
            if e.response is not None:
                self.print_func(f"[JupyterHubAuth] Response status: {e.response.status_code}, data: {e.response.text}", category="Debug")
        except requests.exceptions.RequestException as e:
            self.print_func(f"[JupyterHubAuth] Request error resolving user server: {e}", category="Error")
        except json.JSONDecodeError as e:
            self.print_func(f"[JupyterHubAuth] Error decoding JSON from Hub API: {e}", category="Error")

    def prepare_session(self, session: requests.Session, url: str, **kwargs) -> requests.Session:
        session.headers.update(self._headers)
        return session

    def get_headers(self, **kwargs) -> dict:
        return self._headers

    def get_target_url(self, initial_url: str, **kwargs) -> str:
        # initial_url is the hub_url. If we resolved a user-specific path, use it.
        return self.resolved_target_url or initial_url # Fallback to initial_url if resolution failed

class SageMakerIAMAuthStrategy(AuthStrategy):
    def __init__(self, profile_name: str = None, region_name: str = None, sagemaker_url_or_arn: str = None, console_print_callback=None):
        self.profile_name = profile_name
        self.region_name = region_name
        self.sagemaker_url_or_arn = sagemaker_url_or_arn
        self._jupyter_headers = {} # Renamed from self.jupyter_headers
        self.resolved_target_url = ""
        self.print_func = console_print_callback or print

        # Placeholder for actual SageMaker auth logic
        self.print_func("[SageMakerAuth] SageMakerIAMAuthStrategy is a placeholder and not yet functional.", category="Warning")

    def prepare_session(self, session: requests.Session, url: str, **kwargs) -> requests.Session:
        # Placeholder: In reality, would use boto3 for AWS auth,
        # potentially setting cookies or headers obtained via presigned URL.
        if self._jupyter_headers:
            session.headers.update(self._jupyter_headers)
        return session

    def get_headers(self, **kwargs) -> dict:
        # Placeholder
        return self._jupyter_headers

    def get_target_url(self, initial_url: str, **kwargs) -> str:
        # Placeholder: This would be the SageMaker Jupyter server URL
        return self.resolved_target_url or initial_url 