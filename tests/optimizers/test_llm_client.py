import json

import pytest

from llm.openai_compatible.client import OpenAICompatibleClient
from llm.openai_compatible.config import OpenAICompatibleConfig
from llm.openai_compatible.schemas import build_operator_decision_schema


class _FakeResponsesAPI:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.last_kwargs: dict[str, object] | None = None

    def create(self, **kwargs):
        self.last_kwargs = dict(kwargs)
        return type("FakeResponsesResult", (), {"output_text": self.payload})()


class _FakeChatCompletionsAPI:
    def __init__(self, payload: str | list[str]) -> None:
        self.payload = payload
        self.last_kwargs: dict[str, object] | None = None
        self.call_count = 0

    def create(self, **kwargs):
        self.last_kwargs = dict(kwargs)
        self.call_count += 1
        if isinstance(self.payload, list):
            index = min(self.call_count - 1, len(self.payload) - 1)
            content = self.payload[index]
        else:
            content = self.payload
        message = type("FakeMessage", (), {"content": content})()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeChatResult", (), {"choices": [choice]})()


class _FakeSDK:
    def __init__(
        self,
        *,
        responses_api: _FakeResponsesAPI | None = None,
        chat_api: _FakeChatCompletionsAPI | None = None,
    ) -> None:
        self.responses = responses_api
        self.chat = type(
            "FakeChatNamespace",
            (),
            {"completions": chat_api},
        )()


class _FakeHTTPResponse:
    def __init__(self, payload: str, *, status_code: int = 200, content_type: str = "application/json") -> None:
        self.text = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeHTTPClient:
    def __init__(self, payload: str, *, status_code: int = 200, content_type: str = "application/json") -> None:
        self.payload = payload
        self.status_code = status_code
        self.content_type = content_type
        self.last_url: str | None = None
        self.last_headers: dict[str, object] | None = None
        self.last_json: dict[str, object] | None = None

    def post(self, url: str, *, headers: dict[str, object], json: dict[str, object]) -> _FakeHTTPResponse:
        self.last_url = url
        self.last_headers = dict(headers)
        self.last_json = dict(json)
        return _FakeHTTPResponse(
            self.payload,
            status_code=self.status_code,
            content_type=self.content_type,
        )


def _json_http_response(content_payload: dict[str, object], *, model: str = "gpt-5.4") -> str:
    return json.dumps(
        {
            "id": "resp_123",
            "object": "chat.completion",
            "created": 1,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(content_payload),
                    },
                }
            ],
        }
    )


def _build_config(*, capability_profile: str) -> OpenAICompatibleConfig:
    return OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai",
            "model": "gpt-5.4",
            "capability_profile": capability_profile,
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 256,
            "temperature": 0.2,
            "reasoning": {"effort": "medium"},
        }
    )


def test_responses_native_client_builds_structured_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    responses_api = _FakeResponsesAPI(
        '{"selected_operator_id": "local_refine", "phase": "repair", "rationale": "tighten around hot zone"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="responses_native"),
        sdk_client=_FakeSDK(responses_api=responses_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
    )

    assert response.selected_operator_id == "local_refine"
    assert responses_api.last_kwargs is not None
    assert responses_api.last_kwargs["model"] == "gpt-5.4"
    assert responses_api.last_kwargs["max_output_tokens"] == 256
    assert responses_api.last_kwargs["temperature"] == 0.2
    assert responses_api.last_kwargs["reasoning"] == {"effort": "medium"}
    schema = responses_api.last_kwargs["text"]["format"]["schema"]
    assert responses_api.last_kwargs["text"]["format"]["type"] == "json_schema"
    assert schema["properties"]["selected_operator_id"]["enum"] == ["native_sbx_pm", "local_refine"]


def test_chat_compatible_json_client_normalizes_openai_compatible_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert response.selected_operator_id == "global_explore"
    assert response.phase == "explore"
    assert response.rationale == "widen search"
    assert chat_api.last_kwargs is not None
    assert chat_api.last_kwargs["model"] == "gpt-5.4"
    assert chat_api.last_kwargs["response_format"] == {"type": "json_object"}
    assert chat_api.last_kwargs["messages"][0]["role"] == "system"
    assert chat_api.last_kwargs["messages"][1] == {"role": "user", "content": "user prompt"}
    assert "system prompt" in chat_api.last_kwargs["messages"][0]["content"]
    assert "json" in chat_api.last_kwargs["messages"][0]["content"].lower()

def test_chat_compatible_json_client_accepts_markdown_fenced_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '```json\n{"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}\n```'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert response.selected_operator_id == "global_explore"
    assert response.phase == "explore"
    assert response.rationale == "widen search"
def test_chat_compatible_json_client_can_use_direct_http_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    http_client = _FakeHTTPClient(
        _json_http_response(
            {"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}
        )
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "gpt-5.4",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "base_url": "https://rust.cat/v1",
                "max_output_tokens": 256,
                "temperature": 1.0,
            }
        ),
        http_client=http_client,
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert response.selected_operator_id == "global_explore"
    assert http_client.last_url == "https://rust.cat/v1/chat/completions"
    assert http_client.last_headers is not None
    assert http_client.last_headers["Authorization"] == "Bearer test-key"
    assert http_client.last_json is not None
    assert http_client.last_json["model"] == "gpt-5.4"
    assert http_client.last_json["response_format"] == {"type": "json_object"}
    assert http_client.last_json["max_tokens"] == 256

def test_chat_compatible_json_http_request_forwards_reasoning_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    http_client = _FakeHTTPClient(
        _json_http_response(
            {"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}
        )
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "gpt-5.4",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "base_url": "https://rust.cat/v1",
                "max_output_tokens": 256,
                "reasoning": {"effort": "medium"},
            }
        ),
        http_client=http_client,
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert http_client.last_json is not None
    assert http_client.last_json["reasoning"] == {"effort": "medium"}


def test_chat_compatible_json_http_request_merges_extra_body_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_EXTRA_BODY", '{"enable_thinking": false}')
    http_client = _FakeHTTPClient(
        _json_http_response(
            {"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"},
            model="qwen3.6-plus",
        )
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "qwen3.6-plus",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "base_url": "https://qwen.example/v1",
                "max_output_tokens": 256,
                "reasoning": {"effort": "medium"},
            }
        ),
        http_client=http_client,
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert http_client.last_json is not None
    assert http_client.last_json["reasoning"] == {"effort": "medium"}
    assert http_client.last_json["enable_thinking"] is False


def test_chat_compatible_json_http_request_omits_reasoning_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    http_client = _FakeHTTPClient(
        _json_http_response(
            {"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}
        )
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "gpt-5.4",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "base_url": "https://rust.cat/v1",
                "max_output_tokens": 96,
                "temperature": 0.7,
            }
        ),
        http_client=http_client,
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert http_client.last_json is not None
    assert http_client.last_json["max_tokens"] == 96
    assert "reasoning" not in http_client.last_json


def test_config_rejects_non_mapping_extra_body_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_EXTRA_BODY", '["enable_thinking", false]')
    config = OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai-compatible",
            "model": "qwen3.6-plus",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        }
    )

    with pytest.raises(ValueError, match="LLM_EXTRA_BODY"):
        config.resolve_extra_body()


def test_chat_compatible_json_client_injects_json_instruction_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="select one operator",
        user_prompt="candidate set only",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert chat_api.last_kwargs is not None
    combined_messages = " ".join(
        str(message["content"]) for message in chat_api.last_kwargs["messages"]
    ).lower()
    assert "json" in combined_messages


def test_chat_compatible_json_client_initial_prompt_includes_exact_operator_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI('{"selected_operator_id": "global_explore"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "selected_operator_id" in system_message
    assert "native_sbx_pm" in system_message
    assert "global_explore" in system_message
    assert "exactly" in system_message.lower()


def test_operator_decision_schema_requires_only_selected_operator_id() -> None:
    schema = build_operator_decision_schema(("native_sbx_pm", "local_refine"))

    assert schema["required"] == ["selected_operator_id"]
    assert schema["properties"]["selected_operator_id"]["enum"] == ["native_sbx_pm", "local_refine"]
    assert "selected_semantic_task" in schema["properties"]
    assert "selected_semantic_task" not in schema["required"]
    assert "phase" in schema["properties"]
    assert "rationale" in schema["properties"]


def test_operator_prior_advice_schema_requires_operator_priors() -> None:
    from llm.openai_compatible.schemas import build_operator_prior_advice_schema

    schema = build_operator_prior_advice_schema(("sink_shift", "component_jitter_1"))

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "operator_priors" in schema["required"]
    operator_prior_items = schema["properties"]["operator_priors"]["items"]
    assert operator_prior_items["properties"]["operator_id"]["enum"] == [
        "sink_shift",
        "component_jitter_1",
    ]
    assert operator_prior_items["properties"]["prior"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["prior"]["maximum"] == 1.0
    assert operator_prior_items["properties"]["risk"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["risk"]["maximum"] == 1.0
    assert operator_prior_items["properties"]["confidence"]["minimum"] == 0.0
    assert operator_prior_items["properties"]["confidence"]["maximum"] == 1.0


def test_chat_compatible_json_client_parses_operator_prior_advice() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"phase":"post_feasible_expand","rationale":"balance local cleanup and expansion",'
        '"semantic_task_priors":[{"semantic_task":"local_polish","prior":0.6,"risk":0.2,"confidence":0.7}],'
        '"operator_priors":['
        '{"operator_id":"anchored_component_jitter","prior":0.7,"risk":0.2,"confidence":0.8,"rationale":"bounded local polish"},'
        '{"operator_id":"sink_shift","prior":0.3,"risk":0.5,"confidence":0.4,"rationale":"limited sink alignment"}'
        "]}"
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    advice = client.request_operator_prior_advice(
        system_prompt="return priors",
        user_prompt="{}",
        candidate_operator_ids=("anchored_component_jitter", "sink_shift"),
    )

    assert advice.phase == "post_feasible_expand"
    assert advice.rationale == "balance local cleanup and expansion"
    assert advice.operator_priors[0].operator_id == "anchored_component_jitter"
    assert advice.operator_priors[0].prior == pytest.approx(0.7)
    assert advice.operator_priors[0].risk == pytest.approx(0.2)
    assert advice.operator_priors[0].confidence == pytest.approx(0.8)
    assert advice.semantic_task_priors[0].semantic_task == "local_polish"
    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "operator_priors" in system_message
    assert "selected_operator_id" not in system_message


def test_operator_prior_advice_rejects_unknown_operator_id() -> None:
    chat_api = _FakeChatCompletionsAPI('{"operator_priors":[{"operator_id":"not_in_pool","prior":1.0}]}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_prior_advice(
            system_prompt="return priors",
            user_prompt="{}",
            candidate_operator_ids=("anchored_component_jitter", "sink_shift"),
        )


def test_chat_compatible_json_prompt_marks_phase_and_rationale_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI('{"selected_operator_id": "global_explore"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"]).lower()
    assert "required key: selected_operator_id" in system_message
    assert "optional keys: phase, rationale, selected_intent, selected_semantic_task" in system_message


def test_chat_compatible_json_client_accepts_minimal_operator_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI('{"selected_operator_id": "local_refine"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "local_refine"),
    )

    assert response.selected_operator_id == "local_refine"
    assert response.phase == ""
    assert response.rationale == ""


def test_chat_compatible_json_schema_allows_optional_selected_intent() -> None:
    schema = build_operator_decision_schema(("native_sbx_pm", "slide_sink"))

    assert "selected_intent" in schema["properties"]
    assert "selected_intent" not in schema["required"]


def test_chat_compatible_json_client_accepts_payload_without_selected_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "global_explore", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert response.selected_operator_id == "global_explore"
    assert response.selected_intent is None
    assert response.selected_semantic_task == "global_layout_expand"


def test_chat_compatible_json_client_preserves_selected_semantic_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "sink_resize", "selected_semantic_task": "sink_budget_shape"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "sink_resize"),
    )

    assert response.selected_operator_id == "sink_resize"
    assert response.selected_semantic_task == "sink_budget_shape"


def test_chat_compatible_json_client_accepts_operator_id_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI('{"operator_id": "global_explore"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert response.selected_operator_id == "global_explore"
    assert response.raw_payload["selected_operator_id"] == "global_explore"


def test_chat_compatible_json_client_recovers_operator_id_from_rationale_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": ":", "rationale": "choose move_hottest_cluster_toward_sink for immediate thermal relief"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "move_hottest_cluster_toward_sink", "slide_sink"),
    )

    assert response.selected_operator_id == "move_hottest_cluster_toward_sink"
    assert response.raw_payload["selected_operator_id"] == "move_hottest_cluster_toward_sink"


def test_chat_compatible_json_client_retries_invalid_operator_id_before_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ":"}',
            '{"selected_operator_id": "slide_sink"}',
        ]
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "Kimi-K2",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "max_output_tokens": 256,
                "retry": {"max_attempts": 2},
            }
        ),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "slide_sink"),
    )

    assert response.selected_operator_id == "slide_sink"
    assert chat_api.call_count == 2


def test_request_operator_decision_records_attempt_trace_for_retry_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ":"}',
            '{"selected_operator_id": "slide_sink"}',
        ]
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "Kimi-K2",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "max_output_tokens": 256,
                "retry": {"max_attempts": 2},
            }
        ),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )
    attempt_trace: list[dict[str, object]] = []

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "slide_sink"),
        attempt_trace=attempt_trace,
    )

    assert response.selected_operator_id == "slide_sink"
    assert len(attempt_trace) == 2
    assert attempt_trace[0]["valid"] is False
    assert "outside the requested operator registry" in str(attempt_trace[0]["error"])
    assert attempt_trace[1]["valid"] is True
    assert attempt_trace[1]["selected_operator_id"] == "slide_sink"


def test_chat_compatible_json_client_raises_after_retry_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ""}',
            '{"selected_operator_id": ":"}',
        ]
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "Kimi-K2",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "max_output_tokens": 256,
                "retry": {"max_attempts": 2},
            }
        ),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_decision(
            system_prompt="system prompt",
            user_prompt="user prompt",
            candidate_operator_ids=("native_sbx_pm", "slide_sink"),
        )

    assert chat_api.call_count == 2


def test_chat_compatible_json_client_strengthens_retry_prompt_after_invalid_operator_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ""}',
            '{"selected_operator_id": "slide_sink"}',
        ]
    )
    client = OpenAICompatibleClient(
        OpenAICompatibleConfig.from_dict(
            {
                "provider": "openai-compatible",
                "model": "Kimi-K2",
                "capability_profile": "chat_compatible_json",
                "performance_profile": "balanced",
                "api_key_env_var": "TEST_OPENAI_API_KEY",
                "max_output_tokens": 256,
                "retry": {"max_attempts": 2},
            }
        ),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "slide_sink"),
    )

    assert chat_api.last_kwargs is not None
    retry_system_prompt = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "previous response was invalid" in retry_system_prompt.lower()
    assert "slide_sink" in retry_system_prompt


def test_client_rejects_operator_ids_outside_requested_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    responses_api = _FakeResponsesAPI(
        '{"selected_operator_id": "outside_registry", "phase": "repair", "rationale": "invalid"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="responses_native"),
        sdk_client=_FakeSDK(responses_api=responses_api),
    )

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_decision(
            system_prompt="system prompt",
            user_prompt="user prompt",
            candidate_operator_ids=("native_sbx_pm", "local_refine"),
        )


def test_config_resolves_api_key_from_dotenv_when_process_env_missing(tmp_path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("TEST_OPENAI_API_KEY=dotenv-key\n", encoding="utf-8")
    config = _build_config(capability_profile="responses_native")

    assert config.resolve_api_key({}, dotenv_path=dotenv_path) == "dotenv-key"

def test_config_resolves_model_from_model_env_var_before_literal(tmp_path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("LLM_MODEL=qwen3.6-plus\n", encoding="utf-8")
    config = OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai-compatible",
            "model": "gpt-5.4",
            "model_env_var": "LLM_MODEL",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        }
    )

    assert config.resolve_model(dotenv_path=dotenv_path) == "qwen3.6-plus"


def test_config_raises_when_model_and_model_env_var_are_both_missing() -> None:
    config = OpenAICompatibleConfig.from_dict(
        {
            "provider": "openai-compatible",
            "model_env_var": "LLM_MODEL",
            "capability_profile": "chat_compatible_json",
            "performance_profile": "balanced",
            "api_key_env_var": "TEST_OPENAI_API_KEY",
            "max_output_tokens": 128,
        }
    )

    with pytest.raises(RuntimeError, match="Missing model"):
        config.resolve_model(environ={})


def test_config_resolves_api_key_from_main_repo_dotenv_when_running_in_worktree(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    worktree_root = repo_root / ".worktrees" / "llm-route-recovery"
    common_git_dir = repo_root / ".git"
    worktree_git_dir = common_git_dir / "worktrees" / "llm-route-recovery"
    repo_root.mkdir(parents=True, exist_ok=True)
    worktree_root.mkdir(parents=True, exist_ok=True)
    worktree_git_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / ".env").write_text("TEST_OPENAI_API_KEY=repo-dotenv-key\n", encoding="utf-8")
    (worktree_root / ".git").write_text(f"gitdir: {worktree_git_dir}\n", encoding="utf-8")
    monkeypatch.chdir(worktree_root)
    config = _build_config(capability_profile="responses_native")

    assert config.resolve_api_key({}) == "repo-dotenv-key"


def test_matrix_llm_profiles_include_gpt_5_4_alias(monkeypatch):
    from llm.openai_compatible.profile_loader import load_provider_profile_overlay

    monkeypatch.setenv("GPT_PROXY_API_KEY", "gpt-key")
    monkeypatch.setenv("GPT_PROXY_BASE_URL", "https://gpt.example/v1")
    monkeypatch.setenv("QWEN_PROXY_API_KEY", "qwen-key")
    monkeypatch.setenv("QWEN_PROXY_BASE_URL", "https://qwen.example/v1")
    monkeypatch.setenv("DEEPSEEK_PROXY_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_PROXY_BASE_URL", "https://deepseek.example/v1")
    monkeypatch.setenv("GEMMA4_API_KEY", "gemma-key")
    monkeypatch.setenv("GEMMA4_BASE_URL", "http://127.0.0.1:8000/v1")

    expected_models = {
        "gpt_5_4": "gpt-5.4",
        "qwen3_6_plus": "qwen3.6-plus",
        "glm_5": "glm-5",
        "minimax_m2_5": "MiniMax-M2.5",
        "deepseek_v4_flash": "DeepSeek-V4-Flash",
        "gemma4": "gemma-4",
    }

    for profile_id, model in expected_models.items():
        overlay = load_provider_profile_overlay(profile_id)
        assert overlay["LLM_MODEL"] == model


def test_operator_rank_advice_schema_requires_ranked_operators() -> None:
    from llm.openai_compatible.schemas import build_operator_rank_advice_schema

    schema = build_operator_rank_advice_schema(("sink_shift", "component_jitter_1"))

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "ranked_operators" in schema["required"]
    ranked_items = schema["properties"]["ranked_operators"]["items"]
    assert ranked_items["additionalProperties"] is False
    assert ranked_items["required"] == [
        "operator_id",
        "semantic_task",
        "score",
        "risk",
        "confidence",
        "rationale",
    ]
    assert ranked_items["properties"]["operator_id"]["enum"] == [
        "sink_shift",
        "component_jitter_1",
    ]
    for key in ("score", "risk", "confidence"):
        assert ranked_items["properties"][key]["minimum"] == 0.0
        assert ranked_items["properties"][key]["maximum"] == 1.0


def test_chat_compatible_json_client_parses_operator_rank_advice() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"phase":"post_feasible_expand",'
        '"rationale":"rank sink alignment above local cleanup",'
        '"ranked_operators":['
        '{"operator_id":"sink_shift","semantic_task":"sink_alignment","score":0.82,'
        '"risk":0.22,"confidence":0.74,"rationale":"align sink"},'
        '{"operator_id":"component_jitter_1","semantic_task":"local_polish","score":0.71,'
        '"risk":0.18,"confidence":0.61,"rationale":"bounded local move"}'
        "]}",
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    advice = client.request_operator_rank_advice(
        system_prompt="return ranked operators",
        user_prompt="{}",
        candidate_operator_ids=("sink_shift", "component_jitter_1"),
    )

    assert advice.phase == "post_feasible_expand"
    assert advice.rationale == "rank sink alignment above local cleanup"
    assert advice.ranked_operators[0].operator_id == "sink_shift"
    assert advice.ranked_operators[0].semantic_task == "sink_alignment"
    assert advice.ranked_operators[0].score == pytest.approx(0.82)
    assert advice.ranked_operators[0].risk == pytest.approx(0.22)
    assert advice.ranked_operators[0].confidence == pytest.approx(0.74)
    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "ranked_operators" in system_message
    assert "operator_priors" not in system_message


def test_operator_rank_advice_rejects_unknown_operator_id() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"ranked_operators":[{"operator_id":"not_in_pool","semantic_task":"local_polish",'
        '"score":0.8,"risk":0.1,"confidence":0.6,"rationale":"bad id"}]}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="outside the requested operator registry"):
        client.request_operator_rank_advice(
            system_prompt="return ranked operators",
            user_prompt="{}",
            candidate_operator_ids=("sink_shift", "component_jitter_1"),
        )


def test_operator_rank_advice_requires_explicit_risk_and_confidence() -> None:
    chat_api = _FakeChatCompletionsAPI(
        '{"ranked_operators":[{"operator_id":"sink_shift","semantic_task":"sink_alignment",'
        '"score":0.8,"confidence":0.6,"rationale":"missing risk"}]}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    with pytest.raises(ValueError, match="risk"):
        client.request_operator_rank_advice(
            system_prompt="return ranked operators",
            user_prompt="{}",
            candidate_operator_ids=("sink_shift", "component_jitter_1"),
        )
