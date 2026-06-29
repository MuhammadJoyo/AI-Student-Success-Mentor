"""
services/gemini_service.py

Single point of contact with the Gemini API for the entire
AI Student Success Mentor system.

Architectural contract (see project README for full design):
    - No agent is allowed to import the google-genai SDK directly.
      Every agent calls GeminiService.generate(prompt) instead.
    - This service does NOT know about careers, skills, or internships.
      It only knows how to talk to Gemini and what to do if that fails.
    - On any failure, this service returns a generic, clearly-labeled
      fallback string rather than raising an exception up to the caller.
      It is each AGENT's responsibility to detect that fallback signal
      (via GeminiService.last_call_used_fallback) and substitute its own
      domain-specific, rule-based answer built from local data.
      This file intentionally contains no career/skill/internship logic.
"""

import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Load variables from a .env file into the process environment.
# Safe to call multiple times; does nothing if .env is missing.
load_dotenv()

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """
    Raised only for programmer errors (e.g. missing configuration)
    that should never occur in a correctly deployed environment.
    Runtime failures talking to Gemini (timeouts, quota, bad response)
    are NOT raised — they are handled internally and turned into a
    fallback response instead. See module docstring.
    """
    pass


class GeminiService:
    """
    Thin, production-safe wrapper around the google-genai SDK.

    Responsibilities:
        - Read GEMINI_API_KEY from the environment (.env)
        - Lazily initialize a single google.genai.Client instance
        - Expose a simple generate(prompt) -> str method
        - Catch all Gemini-related failures and degrade gracefully
          instead of crashing the calling agent / orchestrator

    Usage:
        gemini = GeminiService()
        text = gemini.generate("Suggest a career path for a CS student.")

        if gemini.last_call_used_fallback:
            # caller should substitute its own rule-based answer
            ...
    """

    # Default model used if GEMINI_MODEL is not set in .env.
    # Kept here as a single constant so it's easy to bump for the
    # whole system without hunting through agent code.
    DEFAULT_MODEL = "gemini-2.5-flash"

    # Generic fallback text returned when Gemini cannot be reached.
    # This is intentionally domain-agnostic — agents are expected to
    # replace it with their own rule-based content, not display it
    # to the end user as-is.
    FALLBACK_RESPONSE = (
        "[GEMINI_UNAVAILABLE] AI generation is temporarily unavailable. "
        "A rule-based fallback should be used for this section."
    )

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """
        Initialize the Gemini client.

        Args:
            api_key: Optional override for the API key. If not provided,
                      GEMINI_API_KEY is read from the environment (.env).
            model:    Optional override for the model name. If not provided,
                      GEMINI_MODEL is read from the environment, falling
                      back to DEFAULT_MODEL.

        Note:
            We deliberately do NOT raise if the API key is missing.
            A missing key is treated as "Gemini unavailable" so that the
            whole system can still run end-to-end in fallback mode —
            this is required behavior per the project spec, not an
            oversight.
        """
        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)

        # Tracks whether the most recent generate() call had to fall back.
        # Agents read this flag right after calling generate() to decide
        # whether to use the returned text or build their own rule-based
        # response instead.
        self.last_call_used_fallback: bool = False

        self._client: genai.Client | None = None

        if not self._api_key:
            logger.warning(
                "GEMINI_API_KEY not found in environment. "
                "GeminiService will operate in fallback-only mode."
            )
            return

        try:
            self._client = genai.Client(api_key=self._api_key)
        except Exception:
            # Client construction failing (e.g. malformed key string)
            # should not crash the app at import/startup time.
            logger.exception("Failed to initialize Gemini client.")
            self._client = None

    def generate(self, prompt: str, temperature: float = 0.7, max_output_tokens: int = 1024) -> str:
        """
        Generate text from Gemini for the given prompt.

        Args:
            prompt: The full prompt text to send to Gemini.
            temperature: Sampling temperature (0.0 = deterministic, higher = more creative).
            max_output_tokens: Upper bound on response length.

        Returns:
            The model's response text on success.
            GeminiService.FALLBACK_RESPONSE on any failure.

        This method never raises for runtime/API failures. It only ever
        raises if called with an invalid argument (e.g. empty prompt),
        which is a programmer error, not a Gemini/network failure.
        """
        if not prompt or not prompt.strip():
            raise ValueError("generate() requires a non-empty prompt string.")

        # Reset the flag for this call before attempting anything.
        self.last_call_used_fallback = False

        if self._client is None:
            logger.warning("Gemini client not initialized; returning fallback response.")
            self.last_call_used_fallback = True
            return self.FALLBACK_RESPONSE

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )

            # response.text can be None/empty if the model returns no
            # candidates (e.g. blocked by safety filters) — treat that
            # as a failure too, since downstream agents expect real text.
            text = getattr(response, "text", None)
            if not text or not text.strip():
                logger.warning("Gemini returned an empty response; using fallback.")
                self.last_call_used_fallback = True
                return self.FALLBACK_RESPONSE

            return text.strip()

        except APIError as exc:
            # Covers quota errors, invalid requests, rate limiting,
            # and other structured API-level failures from Gemini.
            logger.error("Gemini API error (code=%s): %s", getattr(exc, "code", "unknown"), exc)
            self.last_call_used_fallback = True
            return self.FALLBACK_RESPONSE

        except Exception:
            # Catches anything unexpected: network timeouts, DNS failures,
            # SDK-internal errors, etc. We log the full traceback for
            # debugging but still return a clean fallback to the caller —
            # an agent should never crash because Gemini had a bad day.
            logger.exception("Unexpected error while calling Gemini.")
            self.last_call_used_fallback = True
            return self.FALLBACK_RESPONSE

    def is_available(self) -> bool:
        """
        Returns True if the client was initialized successfully.
        Does NOT guarantee the next live call will succeed (e.g. the
        network could still drop), but lets callers check configuration
        state cheaply without making an API call.
        """
        return self._client is not None