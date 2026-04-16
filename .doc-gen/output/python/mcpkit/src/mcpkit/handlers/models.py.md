# models.py

**Path:** python/mcpkit/src/mcpkit/handlers/models.py
**Syntax:** python
**Generated:** 2026-04-16 10:47:57

```python
"""
mcpkit.handlers.models - LLM model handler (Ollama).

Provides a simple HTTP-based handler for calling Ollama models.
No SSH logic — assumes Ollama is accessible at the configured endpoint.

Usage:
    from mcpkit.handlers.models import call_ollama

    result = call_ollama(
        model="mistral",
        prompt="What is 2+2?",
        endpoint="http://localhost:11434",
        timeout=60,
        retries=3
    )
    print(result["response"])
"""

import requests
from typing import Optional, Dict, Any

from mcpkit.exceptions import ExecutionError


def call_ollama(
    model: str,
    prompt: str,
    endpoint: str = "http://localhost:11434",
    context: Optional[str] = None,
    timeout: int = 60,
    retries: int = 3,
) -> Dict[str, Any]:
    """
    Call an Ollama model with a prompt.

    Args:
        model: Model name (e.g., "mistral", "llama2")
        prompt: The prompt to send to the model
        endpoint: Ollama API endpoint (default: http://localhost:11434)
        context: Optional system context or instructions (prepended to prompt)
        timeout: Request timeout in seconds
        retries: Number of times to retry on failure

    Returns:
        Dict with keys:
            - response: The model's text response
            - model: The model name used
            - done: Whether the model finished generating
            - context: Context tokens (if returned by Ollama)

    Raises:
        ExecutionError: If the call fails after retries exhausted
    """
    # Build full prompt with context if provided
    full_prompt = prompt
    if context:
        full_prompt = f"{context}\n\n{prompt}"

    url = f"{endpoint}/api/generate"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }

    last_error = None

    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            return {
                "response": data.get("response", ""),
                "model": data.get("model", model),
                "done": data.get("done", False),
                "context": data.get("context", None),
            }

        except requests.exceptions.Timeout as e:
            last_error = f"Timeout (attempt {attempt + 1}/{retries}): {e}"
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection error (attempt {attempt + 1}/{retries}): {e}"
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP error (attempt {attempt + 1}/{retries}): {e}"
        except (ValueError, KeyError) as e:
            last_error = f"Response parsing error: {e}"

        if attempt < retries - 1:
            # Wait a bit before retrying (simple backoff)
            import time
            time.sleep(2 ** attempt)

    # All retries exhausted
    raise ExecutionError(
        f"Failed to call Ollama model '{model}' at {endpoint}: {last_error}"
    )


def list_ollama_models(
    endpoint: str = "http://localhost:11434",
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    List available models on an Ollama instance.

    Args:
        endpoint: Ollama API endpoint
        timeout: Request timeout in seconds

    Returns:
        Dict with "models" key containing list of model info dicts

    Raises:
        ExecutionError: If the call fails
    """
    url = f"{endpoint}/api/tags"

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ExecutionError(f"Failed to list Ollama models: {e}")
```
