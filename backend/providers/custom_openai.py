"""Custom OpenAI-compatible endpoint provider."""

import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from .base import LLMProvider
from ..settings import get_settings

# Sensitive key patterns for sanitization
_SANITIZE_KEYS = {
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "secret_key",
    "secretkey",
    "secret-key",
    "token",
    "access_token",
    "accesstoken",
    "access-token",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "bearer",
    "auth_token",
    "key",
    "private_key",
    "privatekey",
    "private-key",
    "password",
    "passwd",
    "pwd",
    "signature",
    "sign",
}


def _sanitize_header(key: str, value: str) -> str:
    """Mask sensitive values in headers."""
    key_lower = key.lower()
    value_lower = value.lower()

    # Check if header name or value contains sensitive keywords
    if any(
        san_key in key_lower for san_key in ["authorization", "api-key", "x-api-key"]
    ):
        # Mask the value
        if "bearer" in value_lower:
            # Mask bearer token
            parts = value.split()
            if len(parts) >= 2:
                rest = parts[1]
                if len(rest) > 8:
                    return f"{parts[0]} {rest[:4]}...{rest[-4:]}"
                else:
                    return f"{parts[0]} ****"
        else:
            # Generic masking for other auth headers
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return "****"
    return value


def _sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive keys from dictionary."""
    if not isinstance(data, dict):
        return data
    return {
        k: v
        for k, v in data.items()
        if not any(san_key in k.lower() for san_key in _SANITIZE_KEYS)
    }


class CustomOpenAIProvider(LLMProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def _get_config(self) -> tuple[str, str, str]:
        """Get custom endpoint configuration."""
        settings = get_settings()
        name = settings.custom_endpoint_name or "Custom"
        url = settings.custom_endpoint_url or ""
        api_key = settings.custom_endpoint_api_key or ""
        return name, url, api_key

    def _parse_error_response(self, response, model: str, name: str) -> dict:
        """
        Parse error response from OpenAI-compatible endpoints.
        Handles various error formats from different providers.
        """
        status_code = response.status_code
        raw_text = response.text[:1000]  # Limit for safety

        # Default values
        error_type = "unknown_error"
        message = raw_text

        # Try to parse JSON error
        try:
            error_json = response.json()

            # OpenAI format: {"error": {"message": "...", "type": "...", "code": "..."}}
            if "error" in error_json:
                err = error_json["error"]
                if isinstance(err, dict):
                    message = err.get("message") or err.get("msg") or str(err)
                    error_type = err.get("type") or err.get("code") or "api_error"
                else:
                    message = str(err)

            # Alternative format: {"message": "...", "code": "..."}
            elif "message" in error_json:
                message = error_json["message"]
                error_type = error_json.get("code", "api_error")

            # NanoGPT specific format (if any)
            elif "detail" in error_json:
                message = error_json["detail"]
                error_type = "validation_error"

        except (json.JSONDecodeError, KeyError):
            # Not JSON, use raw text
            pass

        # Ensure message is not empty
        if not message or not message.strip():
            message = (
                raw_text
                if raw_text
                else f"HTTP {status_code} (No error message provided)"
            )

        # If message is still just brackets (empty JSON), add hint
        if message.strip() == "{}":
            message = f"HTTP {status_code} (Empty JSON response)"

        # Categorize by status code
        if status_code == 429:
            error_type = "rate_limit"
            if "rate" not in message.lower():
                message = f"Rate limited: {message}"
        elif status_code == 401:
            error_type = "auth_error"
        elif status_code == 403:
            error_type = "forbidden"
        elif status_code == 404:
            error_type = "model_not_found"
        elif status_code == 503:
            error_type = "service_unavailable"
        elif status_code >= 500:
            error_type = "server_error"

        # Create user-friendly display message
        display_message = f"[{name}] [{model}] {error_type.upper()}: {message}"

        return {
            "error_type": error_type,
            "message": message,
            "display_message": display_message,
            "raw_response": raw_text,
        }

    async def _log_request_response(
        self,
        provider_name: str,
        model: str,
        url: str,
        request_headers: Dict[str, str],
        request_body: Dict[str, Any],
        response_status: int,
        response_headers: Dict[str, str],
        response_body: Dict[str, Any],
    ) -> None:
        """
        Log complete request/response details in ProxyPal format.

        Format matches: v1-chat-completions-*.log
        """
        from ..error_logger import log_event

        timestamp = datetime.now(timezone.utc).isoformat()

        # Build comprehensive log entry in ProxyPal format
        log_lines = []
        log_lines.append("=== REQUEST INFO ===")
        log_lines.append("Version: LLM-Council-Plus-1.0")
        log_lines.append(f"URL: {url}/chat/completions")
        log_lines.append("Method: POST")
        log_lines.append(f"Timestamp: {timestamp}")
        log_lines.append("")

        log_lines.append("=== HEADERS ===")
        for key, value in request_headers.items():
            log_lines.append(f"{key}: {_sanitize_header(key, value)}")
        log_lines.append("")

        log_lines.append("=== REQUEST BODY ===")
        log_lines.append(
            json.dumps(_sanitize_dict(request_body), indent=2, default=str)
        )
        log_lines.append("")

        log_lines.append("=== API REQUEST 1 ===")
        log_lines.append(f"Timestamp: {timestamp}")
        log_lines.append(f"Upstream URL: {url}/chat/completions")
        log_lines.append("HTTP Method: POST")
        log_lines.append(f"Auth: provider={provider_name}")
        log_lines.append("")
        log_lines.append("Headers:")
        for key, value in request_headers.items():
            log_lines.append(f"{key}: {_sanitize_header(key, value)}")
        log_lines.append("")
        log_lines.append("Body:")
        log_lines.append(
            json.dumps(_sanitize_dict(request_body), indent=2, default=str)
        )
        log_lines.append("")

        log_lines.append("=== API RESPONSE 1 ===")
        log_lines.append(f"Timestamp: {timestamp}")
        log_lines.append("")
        log_lines.append(f"Status: {response_status}")
        log_lines.append("Headers:")
        for key, value in response_headers.items():
            log_lines.append(f"{key}: {value}")
        log_lines.append("")
        log_lines.append("Body:")
        log_lines.append(json.dumps(response_body, indent=2, default=str))
        log_lines.append("")

        log_lines.append("=== RESPONSE ===")
        log_lines.append(f"Status: {response_status}")
        log_lines.append("")
        log_lines.append(json.dumps(response_body, indent=2, default=str))

        log_content = "\n".join(log_lines)

        # Log as DEBUG level event
        await log_event(
            event_type="v1_chat_completions",
            data={"log_content": log_content},
            level="DEBUG",
        )

    async def query(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        timeout: float = 600.0,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        name, base_url, api_key = self._get_config()

        if not base_url:
            return {
                "error": True,
                "error_message": f"{name} endpoint URL not configured",
            }

        # Strip prefix if present
        model = model_id.removeprefix("custom:")

        # Normalize URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Build request body for logging
            request_body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )

                # Parse response body for logging
                response_data = response.json() if response.status_code == 200 else {}

                # Log complete request/response in ProxyPal format
                await self._log_request_response(
                    provider_name=name,
                    model=model,
                    url=base_url,
                    request_headers=headers,
                    request_body=request_body,
                    response_status=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response_data,
                )

                if response.status_code != 200:
                    error_info = self._parse_error_response(response, model, name)

                    # Log the error
                    from ..error_logger import log_model_error

                    await log_model_error(
                        model=model,
                        provider=name,
                        error_type=error_info["error_type"],
                        status_code=response.status_code,
                        message=error_info["message"],
                        raw_response=error_info.get("raw_response"),
                    )

                    return {
                        "error": True,
                        "error_type": error_info["error_type"],
                        "error_code": response.status_code,
                        "error_message": error_info["display_message"],
                    }

                data = response_data
                message = data["choices"][0]["message"]

                # Extract content - standard field
                content = message.get("content") or ""

                # For thinking/reasoning models (Kimi K2, DeepSeek, etc.)
                # Check for reasoning fields that may contain the actual response
                reasoning = (
                    message.get("reasoning_content")  # Moonshot Kimi K2 official
                    or message.get("reasoning")  # Together.ai, some providers
                    or message.get("reasoning_details")  # Other providers
                    or message.get("thought")  # Some other models
                    or ""
                )

                # If content is empty but reasoning exists, use reasoning
                if not content and reasoning:
                    content = reasoning
                # If both exist, prepend reasoning as collapsed details
                elif content and reasoning:
                    content = f"<details><summary>Reasoning Process</summary>\n\n{reasoning}\n\n</details>\n\n{content}"

                # Debug: If content is still empty, log the keys to help identify the issue
                if not content and not reasoning:
                    from ..error_logger import log_model_error

                    await log_model_error(
                        model=model,
                        provider=name,
                        error_type="empty_response_debug",
                        message=f"Empty content/reasoning. Available keys: {list(message.keys())}",
                        raw_response=json.dumps(message, default=str)[:2000],
                    )

                return {"content": content, "reasoning": reasoning, "error": False}

        except httpx.TimeoutException as e:
            # Timeout error - capture details
            from ..error_logger import log_model_error

            error_msg = f"Request timed out after {timeout}s"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="timeout",
                message=error_msg,
                raw_response=f"Timeout type: {type(e).__name__}",
            )
            return {
                "error": True,
                "error_type": "timeout",
                "error_message": f"[{name}] [{model}] TIMEOUT: {error_msg}",
            }
        except httpx.ConnectError as e:
            # Connection error
            from ..error_logger import log_model_error

            error_msg = f"Connection failed to {base_url}"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="connection_error",
                message=error_msg,
                raw_response=f"Error type: {type(e).__name__}",
            )
            return {
                "error": True,
                "error_type": "connection_error",
                "error_message": f"[{name}] [{model}] CONNECTION_ERROR: {error_msg}",
            }
        except Exception as e:
            # Generic error - capture as much detail as possible
            from ..error_logger import log_model_error

            error_type_name = type(e).__name__
            error_msg = (
                str(e) if str(e) else f"Unexpected {error_type_name} (no message)"
            )

            await log_model_error(
                model=model,
                provider=name,
                error_type="exception",
                message=error_msg,
                raw_response=f"Exception type: {error_type_name}, Args: {e.args}",
            )
            return {
                "error": True,
                "error_type": "exception",
                "error_message": f"[{name}] [{model}] {error_type_name.upper()}: {error_msg}",
            }

    async def get_models(self) -> List[Dict[str, Any]]:
        name, base_url, api_key = self._get_config()

        if not base_url:
            return []

        # Normalize URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/models", headers=headers)

                if response.status_code != 200:
                    return []

                data = response.json()
                models = []

                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    if not model_id:
                        continue

                    mid = model_id.lower()
                    # Filter out non-chat models
                    if any(
                        x in mid
                        for x in [
                            "embed",
                            "whisper",
                            "tts",
                            "dall-e",
                            "audio",
                            "transcribe",
                        ]
                    ):
                        continue

                    models.append(
                        {
                            "id": f"custom:{model_id}",
                            "name": f"{model_id} [{name}]",
                            "provider": name,
                        }
                    )

                return sorted(models, key=lambda x: x["name"])

        except Exception:
            return []

    async def validate_connection(self, url: str, api_key: str = "") -> Dict[str, Any]:
        """Validate connection to a custom endpoint."""
        if not url:
            return {"success": False, "message": "URL is required"}

        # Normalize URL
        if url.endswith("/"):
            url = url[:-1]

        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/models", headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("data", []))
                    return {
                        "success": True,
                        "message": f"Connected successfully. Found {model_count} models.",
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "message": "Authentication failed. Check your API key.",
                    }
                else:
                    return {
                        "success": False,
                        "message": f"API error: {response.status_code}",
                    }

        except httpx.ConnectError:
            return {"success": False, "message": "Connection failed. Check the URL."}
        except httpx.TimeoutException:
            return {"success": False, "message": "Connection timed out."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def validate_key(self, api_key: str) -> Dict[str, Any]:
        """Validate using stored URL."""
        _, base_url, _ = self._get_config()
        return await self.validate_connection(base_url, api_key)
