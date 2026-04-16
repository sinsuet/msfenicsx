import pytest

from llm.openai_compatible.client import OpenAICompatibleClient
from llm.openai_compatible.config import OpenAICompatibleConfig


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


def test_chat_compatible_json_client_can_use_direct_http_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    http_client = _FakeHTTPClient(
        (
            '{"id":"resp_123","object":"chat.completion","created":1,"model":"gpt-5.4",'
            '"choices":[{"index":0,"message":{"role":"assistant","content":"'
            '{\\"selected_operator_id\\":\\"global_explore\\",\\"phase\\":\\"explore\\",'
            '\\"rationale\\":\\"widen search\\"}"}}]}'
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


def test_chat_compatible_json_prompt_demands_phase_and_rationale_fields(
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
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "global_explore"),
    )

    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"]).lower()
    assert "selected_operator_id" in system_message
    assert "phase" in system_message
    assert "rationale" in system_message


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
