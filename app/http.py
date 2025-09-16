"""
HTTP client wrapper with improved error handling for the Clinic Synthesizer Operator.
Provides unified error handling and timeout management for API requests.
"""
from typing import Any, Optional
import requests
from requests.exceptions import RequestException

from .settings import config

class HTTPError(Exception):
    """Base exception for HTTP-related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

class HTTPClient:
    """
    HTTP client wrapper with timeout and error handling.
    
    Usage:
        client = HTTPClient(base_url="http://api.example.com")
        response = client.get("/endpoint")
    """
    
    def __init__(self, base_url: str, timeout: Optional[int] = None):
        """
        Initialize HTTP client with base URL and optional timeout.
        
        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds (default from config)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout or config.API_TIMEOUT
        
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """
        Make HTTP request with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path
            **kwargs: Additional arguments for requests
            
        Returns:
            Any: Parsed JSON response
            
        Raises:
            HTTPError: On request failure or invalid response
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise HTTPError(f"Request to {url} timed out after {self.timeout}s")
            
        except requests.exceptions.ConnectionError as e:
            raise HTTPError(f"Failed to connect to {url}: {str(e)}")
            
        except requests.exceptions.HTTPError as e:
            raise HTTPError(
                f"HTTP {e.response.status_code} error from {url}",
                status_code=e.response.status_code,
                response_text=e.response.text
            )
            
        except RequestException as e:
            raise HTTPError(f"Request to {url} failed: {str(e)}")
            
        except ValueError as e:
            raise HTTPError(f"Invalid JSON response from {url}: {str(e)}")
    
    def get(self, path: str, params: Optional[dict] = None) -> Any:
        """Send GET request."""
        return self._request('GET', path, params=params)
    
    def post(self, path: str, json: Optional[dict] = None) -> Any:
        """Send POST request with JSON data."""
        return self._request('POST', path, json=json)
    
    def put(self, path: str, json: Optional[dict] = None) -> Any:
        """Send PUT request with JSON data."""
        return self._request('PUT', path, json=json)
    
    def delete(self, path: str) -> Any:
        """Send DELETE request."""
        return self._request('DELETE', path)

# Pre-configured clients for services
billing_client = HTTPClient(base_url=config.BILLING_API_URL)
review_client = HTTPClient(base_url=config.REVIEW_API_URL)