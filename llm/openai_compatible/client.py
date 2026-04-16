"""OpenAI-compatible transport wrapper for structured union-controller decisions."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from llm.openai_compatible.config import OpenAICompatibleConfig
from llm.openai_compatible.schemas import build_operator_decision_schema


@dataclass(frozen=True, slots=True)
class OpenAICompatibleDecision:
    selected_operator_id: str
    phase: str
    rationale: str
    provider: str
    model: str
    capability_profile: str
    performance_profile: str
    raw_payload: dict[str, Any]
    selected_intent: str | None = None


class OpenAICompatibleClient:
    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        sdk_client: Any | None = None,
        http_client: Any | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self.config = config
        self._sdk_client = sdk_client
        self._http_client = http_client
        self._environ = os.environ if environ is None else environ

    def request_operator_decision(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
        attempt_trace: list[dict[str, Any]] | None = None,
    ) -> OpenAICompatibleDecision:
        operator_ids = tuple(str(operator_id) for operator_id in candidate_operator_ids)
        if not operator_ids:
            raise ValueError("OpenAICompatibleClient requires at least one candidate operator id.")

        last_error: Exception | None = None
        current_system_prompt = system_prompt
        for attempt_index in range(self.config.max_attempts):
            try:
                raw_text = self._request_raw_text(
                    system_prompt=current_system_prompt,
                    user_prompt=user_prompt,
                    candidate_operator_ids=operator_ids,
                )
                decision = self._parse_decision(raw_text, operator_ids)
                if attempt_trace is not None:
                    attempt_trace.append(
                        {
                            "attempt_index": int(attempt_index + 1),
                            "valid": True,
                            "raw_text": raw_text,
                            "selected_operator_id": decision.selected_operator_id,
                        }
                    )
                return decision
            except ValueError as exc:
                if attempt_trace is not None:
                    attempt_trace.append(
                        {
                            "attempt_index": int(attempt_index + 1),
                            "valid": False,
                            "error": str(exc),
                        }
                    )
                last_error = exc
                current_system_prompt = self._build_retry_system_prompt(
                    system_prompt,
                    operator_ids,
                    str(exc),
                )
            except Exception as exc:
                if attempt_trace is not None:
                    attempt_trace.append(
                        {
                            "attempt_index": int(attempt_index + 1),
                            "valid": False,
                            "error": str(exc),
                        }
                    )
                last_error = exc
                raise
        assert last_error is not None
        raise last_error

    def _request_raw_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        if self.config.capability_profile == "responses_native":
            return self._request_via_responses_native(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
            )
        if self.config.capability_profile == "chat_compatible_json":
            return self._request_via_chat_compatible_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
            )
        raise ValueError(f"Unsupported capability profile '{self.config.capability_profile}'.")

    def _parse_decision(
        self,
        raw_text: str,
        operator_ids: Sequence[str],
    ) -> OpenAICompatibleDecision:
        payload = json.loads(raw_text)
        if "selected_operator_id" not in payload and "operator_id" in payload:
            payload["selected_operator_id"] = payload["operator_id"]
        selected_operator_id = str(payload["selected_operator_id"]).strip()
        if selected_operator_id not in operator_ids:
            recovered_operator_id = self._recover_operator_id_from_text(raw_text, operator_ids)
            if recovered_operator_id is not None:
                selected_operator_id = recovered_operator_id
                payload["selected_operator_id"] = recovered_operator_id
        if selected_operator_id not in operator_ids:
            raise ValueError(
                "LLM selected operator id outside the requested operator registry: "
                f"{selected_operator_id!r} not in {list(operator_ids)}."
            )
        return OpenAICompatibleDecision(
            selected_operator_id=selected_operator_id,
            selected_intent=(
                None
                if payload.get("selected_intent") in (None, "")
                else str(payload.get("selected_intent")).strip()
            ),
            phase=str(payload.get("phase", "")),
            rationale=str(payload.get("rationale", "")),
            provider=self.config.provider,
            model=self.config.model,
            capability_profile=self.config.capability_profile,
            performance_profile=self.config.performance_profile,
            raw_payload=dict(payload),
        )

    def _request_via_responses_native(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        sdk_client = self._resolve_sdk_client()
        schema = build_operator_decision_schema(candidate_operator_ids)
        request_payload: dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_output_tokens": self.config.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "operator_decision",
                    "schema": schema,
                }
            },
        }
        if self.config.temperature is not None:
            request_payload["temperature"] = self.config.temperature
        if self.config.reasoning:
            request_payload["reasoning"] = dict(self.config.reasoning)
        response = sdk_client.responses.create(**request_payload)
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ValueError("Responses API result did not include structured output_text.")
        return output_text

    def _request_via_chat_compatible_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        if self._sdk_client is not None and self._http_client is None:
            return self._request_via_chat_compatible_json_sdk(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                candidate_operator_ids=candidate_operator_ids,
            )
        return self._request_via_chat_compatible_json_http(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            candidate_operator_ids=candidate_operator_ids,
        )

    def _request_via_chat_compatible_json_sdk(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        sdk_client = self._resolve_sdk_client()
        normalized_system_prompt = self._build_chat_json_system_prompt(
            system_prompt,
            user_prompt,
            candidate_operator_ids,
        )
        request_payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": normalized_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.config.max_output_tokens,
        }
        if self.config.temperature is not None:
            request_payload["temperature"] = self.config.temperature
        response = sdk_client.chat.completions.create(**request_payload)
        choices = getattr(response, "choices", None)
        if not isinstance(choices, list) or not choices:
            raise ValueError("Chat-compatible response did not include any choices.")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Chat-compatible response did not include JSON content.")
        return content

    def _request_via_chat_compatible_json_http(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        http_client = self._resolve_http_client()
        normalized_system_prompt = self._build_chat_json_system_prompt(
            system_prompt,
            user_prompt,
            candidate_operator_ids,
        )
        request_payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": normalized_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.config.max_output_tokens,
        }
        if self.config.temperature is not None:
            request_payload["temperature"] = self.config.temperature
        if self.config.reasoning:
            request_payload["reasoning"] = dict(self.config.reasoning)
        response = http_client.post(
            self._resolve_chat_completions_url(),
            headers={
                "Authorization": f"Bearer {self.config.resolve_api_key(self._environ)}",
                "Content-Type": "application/json",
            },
            json=request_payload,
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        return self._extract_chat_content_from_http_response(response)

    @staticmethod
    def _build_chat_json_system_prompt(
        system_prompt: str,
        user_prompt: str,
        candidate_operator_ids: Sequence[str],
    ) -> str:
        normalized_prompt = system_prompt
        combined_prompt = f"{system_prompt}\n{user_prompt}".lower()
        if "json" not in combined_prompt:
            suffix = " Return valid JSON only."
            if normalized_prompt.endswith((" ", "\n")):
                normalized_prompt = f"{normalized_prompt}{suffix.strip()}"
            else:
                normalized_prompt = f"{normalized_prompt}{suffix}"
        return (
            f"{normalized_prompt.rstrip()} "
            "Return exactly one JSON object with the keys selected_operator_id, phase, rationale, "
            "and optional selected_intent. "
            f"The selected_operator_id value must exactly equal one of {list(candidate_operator_ids)}. "
            "If selected_intent is present, keep it short and route-like. "
            "Set phase to a short search-phase label when available. "
            "Set rationale to a brief explanation of the operator choice."
        )

    @staticmethod
    def _recover_operator_id_from_text(raw_text: str, operator_ids: Sequence[str]) -> str | None:
        matches = [operator_id for operator_id in operator_ids if operator_id in raw_text]
        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) == 1:
            return unique_matches[0]
        return None

    @staticmethod
    def _build_retry_system_prompt(
        system_prompt: str,
        operator_ids: Sequence[str],
        error_message: str,
    ) -> str:
        return (
            f"{system_prompt.rstrip()} "
            "Previous response was invalid. "
            "It must return JSON only with the keys selected_operator_id, phase, rationale, "
            "and optional selected_intent. "
            f"The selected_operator_id value must exactly equal one of {list(operator_ids)}. "
            f"Invalid reason: {error_message}"
        )

    @staticmethod
    def _extract_chat_content_from_http_response(response: Any) -> str:
        body = str(getattr(response, "text", "")).strip()
        if not body:
            raise ValueError("Chat-compatible HTTP response did not include a body.")
        payload = OpenAICompatibleClient._parse_http_chat_payload(body)
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Chat-compatible HTTP response did not include any choices.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ValueError("Chat-compatible HTTP response did not include a message payload.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Chat-compatible HTTP response did not include JSON content.")
        return content

    @staticmethod
    def _parse_http_chat_payload(body: str) -> dict[str, Any]:
        stripped = body.strip()
        if stripped.startswith("data:"):
            payloads: list[dict[str, Any]] = []
            for raw_line in stripped.splitlines():
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    continue
                payload = json.loads(chunk)
                if isinstance(payload, dict):
                    payloads.append(payload)
            if not payloads:
                raise ValueError("Chat-compatible HTTP event stream did not include a JSON payload.")
            return payloads[-1]
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError("Chat-compatible HTTP response payload must be a JSON object.")
        return payload

    def _resolve_chat_completions_url(self) -> str:
        base_url = self.config.resolve_base_url(self._environ)
        if base_url:
            return f"{base_url.rstrip('/')}/chat/completions"
        if self.config.provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        raise RuntimeError("Chat-compatible HTTP transport requires a base_url for non-openai providers.")

    def _resolve_http_client(self) -> Any:
        if self._http_client is not None:
            return self._http_client
        timeout_seconds = self.config.timeout_seconds
        self._http_client = httpx.Client(timeout=timeout_seconds)
        return self._http_client

    def _resolve_sdk_client(self) -> Any:
        if self._sdk_client is not None:
            return self._sdk_client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only in live environments without dependency
            raise RuntimeError("The openai package is required for live OpenAI-compatible calls.") from exc

        client_kwargs: dict[str, Any] = {
            "api_key": self.config.resolve_api_key(self._environ),
        }
        base_url = self.config.resolve_base_url(self._environ)
        if base_url:
            client_kwargs["base_url"] = base_url
        timeout_seconds = self.config.timeout_seconds
        if timeout_seconds is not None:
            client_kwargs["timeout"] = timeout_seconds
        self._sdk_client = OpenAI(**client_kwargs)
        return self._sdk_client
