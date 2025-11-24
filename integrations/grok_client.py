"""LLM client wrapper supporting Groq, Grok, and Gemini providers.

This module encapsulates HTTP interaction with OpenAI-compatible chat endpoints.
All providers (Groq, Grok, and Gemini) now use OpenAI-compatible format.
Returns a simple tuple (content, citations, confidence) that BaseAgent can consume.

Environment variables:
    - LLM_PROVIDER: 'groq', 'grok', or 'gemini' (auto-detects by key when omitted)
    - GROQ_API_KEY: API key for Groq
    - GROK_API_KEY: API key for Grok (xAI)
    - GEMINI_API_KEY: API key for Google Gemini
    - MODEL_NAME: Model name, e.g.:
        * Groq: 'llama-3.3-70b-versatile', 'mixtral-8x7b-32768'
        * Grok: 'grok-beta'
        * Gemini: 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp'
    - GROQ_API_URL: Override base URL for Groq (default: https://api.groq.com/openai/v1)
    - GROK_API_URL: Override base URL for Grok (default: https://api.x.ai/v1)
    - GEMINI_API_URL: Override base URL for Gemini (default: https://generativelanguage.googleapis.com/v1beta/openai)

Note: Gemini uses OpenAI-compatible endpoint but requires API key in URL query parameter.
"""
from __future__ import annotations

import os
from typing import List, Tuple
import httpx
import time
import random
import logging

# Simple in-process rate limiter state
_RATE_LAST_TS: float = 0.0

def _respect_min_interval():
    """Sleep to enforce a minimum interval between provider calls.

    Controlled by env LLM_MIN_INTERVAL_S (default 0). This helps avoid 429s on
    accounts with strict RPM. Applies across all agents in this process.
    """
    global _RATE_LAST_TS
    try:
        min_interval = float(os.getenv("LLM_MIN_INTERVAL_S", "0"))
    except Exception:
        min_interval = 0.0
    if min_interval <= 0:
        return
    now = time.monotonic()
    if _RATE_LAST_TS > 0:
        wait = _RATE_LAST_TS + min_interval - now
        if wait > 0:
            logging.info(f"Rate limit: waiting {wait:.2f}s before provider call (min_interval={min_interval}s)")
            time.sleep(wait)
    else:
        logging.info(f"Rate limit: first call, enforcing {min_interval}s baseline delay")
        time.sleep(min_interval)
    _RATE_LAST_TS = time.monotonic()


class LLMClient:
    """Provider-agnostic client for chat completions (Groq, Grok, or Gemini).

    Selection logic:
      - If LLM_PROVIDER set, use it.
      - Else if GEMINI_API_KEY set, use Gemini.
      - Else if GROQ_API_KEY set, use Groq.
      - Else if GROK_API_KEY set, use Grok.
      - Else raise.
    """

    def __init__(self) -> None:
        provider = (os.getenv("LLM_PROVIDER") or "").lower().strip()
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        grok_key = os.getenv("GROK_API_KEY")

        if not provider:
            if gemini_key:
                provider = "gemini"
            elif groq_key:
                provider = "groq"
            elif grok_key:
                provider = "grok"

        if provider not in {"groq", "grok", "gemini"}:
            raise RuntimeError(
                "LLM provider not configured. Set LLM_PROVIDER=groq|grok|gemini and corresponding API key."
            )

        self.provider = provider
        if provider == "groq":
            if not groq_key:
                raise RuntimeError("GROQ_API_KEY not set for provider 'groq'")
            self.api_key = groq_key
            self.base_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1")
            # Model default for Groq
            self.model = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
        elif provider == "grok":  # xAI
            if not grok_key:
                raise RuntimeError("GROK_API_KEY not set for provider 'grok'")
            self.api_key = grok_key
            self.base_url = os.getenv("GROK_API_URL", "https://api.x.ai/v1")
            self.model = os.getenv("MODEL_NAME", "grok")
        else:  # gemini
            if not gemini_key:
                raise RuntimeError("GEMINI_API_KEY not set for provider 'gemini'")
            self.api_key = gemini_key
            # Gemini supports OpenAI-compatible endpoint (note trailing slash is important!)
            self.base_url = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
            self.model = os.getenv("MODEL_NAME", "gemini-2.5-flash")

    def generate(self, instructions: str, prompt: str) -> Tuple[str, List[str], float]:
        # Gemini uses native API, others use OpenAI-compatible
        if self.provider == "gemini":
            return self._generate_gemini(instructions, prompt)
        else:
            return self._generate_openai_compatible(instructions, prompt)

    def _generate_gemini(self, instructions: str, prompt: str) -> Tuple[str, List[str], float]:
        """Generate using Gemini's native API format with x-goog-api-key header.

        Includes graceful fallback for models that are not available (e.g., "-live").
        """
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        # Combine instructions and prompt for Gemini
        combined_text = f"{instructions}\n\n{prompt}"
        payload = {
            "contents": [{"parts": [{"text": combined_text}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
            },
        }

        # Prepare model candidates to try if the first returns 404/400
        model_candidates = [self.model]
        # If user requests a "-live" model that may not be available on REST, try the base flash model
        if self.model.endswith("-live"):
            base_candidate = self.model.replace("-live", "")
            if base_candidate not in model_candidates:
                model_candidates.append(base_candidate)
        # Also add a well-known stable fallback
        if "gemini-2.5-flash" not in model_candidates:
            model_candidates.append("gemini-2.5-flash")
        if "gemini-1.5-flash" not in model_candidates:
            model_candidates.append("gemini-1.5-flash")

        max_retries = int(os.getenv("LLM_RETRY_MAX", "4"))
        base_delay = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))

        last_error = None
        with httpx.Client(timeout=60) as client:
            for model_name in model_candidates:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                attempt = 0
                while True:
                    try:
                        _respect_min_interval()
                        resp = client.post(url, json=payload, headers=headers)
                        # Explicit model-not-found / invalid endpoint handling
                        if resp.status_code in (400, 404):
                            # Capture and move to next candidate
                            last_error = resp.text
                            logging.warning(
                                "Gemini model '%s' not available (status %s). Trying fallback.",
                                model_name,
                                resp.status_code,
                            )
                            break  # break retry loop to try next model

                        if resp.status_code in (429, 500, 502, 503, 504):
                            if attempt >= max_retries:
                                logging.error(
                                    "Gemini returned %s after %s retries for model '%s', giving up.",
                                    resp.status_code,
                                    attempt,
                                    model_name,
                                )
                                resp.raise_for_status()

                            retry_after_hdr = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
                            retry_after_val = 0.0
                            if retry_after_hdr:
                                try:
                                    retry_after_val = float(retry_after_hdr)
                                except Exception:
                                    retry_after_val = 0.0
                            attempt += 1
                            sleep_s = retry_after_val if retry_after_val > 0 else (base_delay * (2 ** (attempt - 1)))
                            sleep_s += random.uniform(0, 0.25 * sleep_s)
                            actual_sleep = min(sleep_s, 15.0)
                            logging.warning(
                                "Gemini returned %s, retry %s/%s in %.2fs (model '%s')",
                                resp.status_code,
                                attempt,
                                max_retries,
                                actual_sleep,
                                model_name,
                            )
                            time.sleep(actual_sleep)
                            continue

                        resp.raise_for_status()
                        data = resp.json()
                        # Parse Gemini response
                        content = ""
                        try:
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    content = parts[0]["text"]
                        except Exception as e:
                            logging.warning(f"Failed to parse Gemini response: {e}")
                            content = str(data)

                        citations: List[str] = []
                        confidence = 0.75
                        return content, citations, confidence
                    except (httpx.TimeoutException, httpx.ConnectError) as e:
                        attempt += 1
                        if attempt > max_retries:
                            logging.error(f"Network error after {attempt} retries: {e}")
                            last_error = str(e)
                            break  # give up on this model candidate
                        sleep_s = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25 * base_delay)
                        actual_sleep = min(sleep_s, 15.0)
                        logging.warning(
                            "Network error, retry %s/%s in %.2fs (model '%s'): %s",
                            attempt,
                            max_retries,
                            actual_sleep,
                            model_name,
                            e,
                        )
                        time.sleep(actual_sleep)

        # If we got here, all candidates failed
        raise RuntimeError(f"Gemini generation failed for all candidates {model_candidates}: {last_error}")

    def _generate_openai_compatible(self, instructions: str, prompt: str) -> Tuple[str, List[str], float]:
        """Generate using OpenAI-compatible API format (Groq, Grok, Gemini)."""
        url = f"{self.base_url}/chat/completions"
        
        # Gemini uses x-goog-api-key header, others use Bearer token
        if self.provider == "gemini":
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            }
        else:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        # Basic, provider-friendly retry with exponential backoff for 429/5xx/network
        max_retries = int(os.getenv("LLM_RETRY_MAX", "4"))
        base_delay = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))
        with httpx.Client(timeout=60) as client:
            attempt = 0
            last_status = None
            while True:
                try:
                    # Rate-limit guard before each provider request
                    _respect_min_interval()
                    resp = client.post(url, json=payload, headers=headers)
                    last_status = resp.status_code
                    # Retry only for transient statuses
                    if resp.status_code in (429, 500, 502, 503, 504):
                        if attempt >= max_retries:
                            logging.error(f"Provider returned {resp.status_code} after {attempt} retries, giving up.")
                            resp.raise_for_status()  # will raise HTTPStatusError
                        # Gather hint from headers
                        retry_after_hdr = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
                        retry_after_val = 0.0
                        if retry_after_hdr:
                            try:
                                retry_after_val = float(retry_after_hdr)
                            except Exception:
                                retry_after_val = 0.0
                        attempt += 1
                        sleep_s = retry_after_val if retry_after_val > 0 else (base_delay * (2 ** (attempt - 1)))
                        sleep_s += random.uniform(0, 0.25 * sleep_s)
                        actual_sleep = min(sleep_s, 15.0)
                        logging.warning(f"Provider returned {resp.status_code}, retry {attempt}/{max_retries} in {actual_sleep:.2f}s")
                        time.sleep(actual_sleep)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    attempt += 1
                    if attempt > max_retries:
                        logging.error(f"Network error after {attempt} retries: {e}")
                        raise
                    sleep_s = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25 * base_delay)
                    actual_sleep = min(sleep_s, 15.0)
                    logging.warning(f"Network error, retry {attempt}/{max_retries} in {actual_sleep:.2f}s: {e}")
                    time.sleep(actual_sleep)

        content = (
            data.get("choices", [{}])[0].get("message", {}).get("content")
            or data.get("choices", [{}])[0].get("text")
            or ""
        )
        # Best-effort citations extraction
        citations = (
            data.get("citations")
            or data.get("choices", [{}])[0].get("message", {}).get("citations")
            or []
        )
        conf = data.get("confidence", 0.75)
        try:
            confidence = float(conf)
        except Exception:
            confidence = 0.75
        confidence = max(0.0, min(1.0, confidence))
        return content, citations, confidence
