from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from optimization.variable_registry import build_current_case_variable_registry


DEFAULT_MODEL = "qwen3.5-plus"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "plan_changes_system.md"


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def load_system_prompt(path: str | Path = DEFAULT_SYSTEM_PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def build_change_prompt(
    *,
    state,
    evaluation: dict[str, Any],
    history_summary: str,
) -> str:
    state_payload = json.dumps(_to_plain_data(state), ensure_ascii=False, indent=2)
    evaluation_payload = json.dumps(evaluation, ensure_ascii=False, indent=2)
    editable_variables = "\n".join(
        "- "
        f"{item.path}: {item.description} "
        f"Bounds=[{item.min_value}, {item.max_value}], {item.step_rule}. "
        f"Priority={item.priority}, Role={item.role}, JointChanges={item.joint_changes}, "
        f"RecommendedDirection={item.recommended_direction}. "
        f"StrategyNote={item.strategy_note}"
        for item in build_current_case_variable_registry()
    )
    return (
        "Current design state:\n"
        f"{state_payload}\n\n"
        "Editable variables for this case:\n"
        f"{editable_variables}\n\n"
        "Current evaluation report:\n"
        f"{evaluation_payload}\n\n"
        "Optimization history summary:\n"
        f"{history_summary}\n\n"
        "Return a JSON object with keys: decision_summary, changes, expected_effects, risk_notes."
    )


def _strip_json_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        text = "\n".join(lines).strip()
    return text


def _decode_first_json_object(raw_text: str) -> dict[str, Any]:
    text = _strip_json_fence(raw_text)
    decoder = json.JSONDecoder()
    last_error: json.JSONDecodeError | None = None

    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(payload, dict):
            return payload

    if last_error is not None:
        raise last_error
    raise json.JSONDecodeError("No JSON object found in model response", text, 0)


def parse_change_proposal(raw_text: str) -> dict[str, Any]:
    payload = _decode_first_json_object(raw_text)
    required_keys = {"decision_summary", "changes", "expected_effects", "risk_notes"}
    missing = required_keys.difference(payload)
    if missing:
        raise ValueError(f"Missing keys in change proposal: {sorted(missing)}")
    if not isinstance(payload["changes"], list):
        raise ValueError("'changes' must be a list.")
    if not isinstance(payload["expected_effects"], list):
        raise ValueError("'expected_effects' must be a list.")
    if not isinstance(payload["risk_notes"], list):
        raise ValueError("'risk_notes' must be a list.")
    return payload


def _post_chat_completion(
    *,
    api_key: str,
    base_url: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    http_request = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DashScope request failed with HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"DashScope request failed: {exc.reason}") from exc


def propose_next_changes(
    *,
    state,
    evaluation: dict[str, Any],
    history_summary: str,
    output_dir: str | Path | None = None,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    enable_thinking: bool = False,
    timeout: float = 120.0,
    system_prompt_path: str | Path = DEFAULT_SYSTEM_PROMPT_PATH,
) -> dict[str, Any]:
    api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set.")

    system_prompt = load_system_prompt(system_prompt_path)
    user_prompt = build_change_prompt(
        state=state,
        evaluation=evaluation,
        history_summary=history_summary,
    )
    request_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "enable_thinking": enable_thinking,
    }
    response_payload = _post_chat_completion(
        api_key=api_key,
        base_url=base_url,
        payload=request_payload,
        timeout=timeout,
    )

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "prompt.txt").write_text(user_prompt, encoding="utf-8")
        (output_dir / "raw_response.json").write_text(
            json.dumps(response_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    message = response_payload["choices"][0]["message"]["content"]
    proposal = parse_change_proposal(message)
    timestamp = datetime.now(timezone.utc).isoformat()
    result = {
        **proposal,
        "model_info": {
            "provider": "dashscope",
            "model": model,
            "base_url": base_url,
            "requested_at_utc": timestamp,
            "usage": response_payload.get("usage", {}),
        },
    }

    if output_dir is not None:
        (output_dir / "proposal.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return result
