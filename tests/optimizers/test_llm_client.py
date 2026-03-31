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
        '{"selected_operator_id": "sbx_pm_global", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global"),
    )

    assert response.selected_operator_id == "sbx_pm_global"
    assert response.phase == "explore"
    assert response.rationale == "widen search"
    assert chat_api.last_kwargs is not None
    assert chat_api.last_kwargs["model"] == "gpt-5.4"
    assert chat_api.last_kwargs["response_format"] == {"type": "json_object"}
    assert chat_api.last_kwargs["messages"][0]["role"] == "system"
    assert chat_api.last_kwargs["messages"][1] == {"role": "user", "content": "user prompt"}
    assert "system prompt" in chat_api.last_kwargs["messages"][0]["content"]
    assert "json" in chat_api.last_kwargs["messages"][0]["content"].lower()


def test_chat_compatible_json_client_injects_json_instruction_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "sbx_pm_global", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="select one operator",
        user_prompt="candidate set only",
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global"),
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
    chat_api = _FakeChatCompletionsAPI('{"selected_operator_id": "sbx_pm_global"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global"),
    )

    assert chat_api.last_kwargs is not None
    system_message = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "selected_operator_id" in system_message
    assert "native_sbx_pm" in system_message
    assert "sbx_pm_global" in system_message
    assert "exactly" in system_message.lower()


def test_chat_compatible_json_prompt_demands_phase_and_rationale_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": "sbx_pm_global", "phase": "explore", "rationale": "widen search"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global"),
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
    chat_api = _FakeChatCompletionsAPI('{"operator_id": "sbx_pm_global"}')
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "sbx_pm_global"),
    )

    assert response.selected_operator_id == "sbx_pm_global"
    assert response.raw_payload["selected_operator_id"] == "sbx_pm_global"


def test_chat_compatible_json_client_recovers_operator_id_from_rationale_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        '{"selected_operator_id": ":", "rationale": "choose hot_pair_to_sink for immediate thermal relief"}'
    )
    client = OpenAICompatibleClient(
        _build_config(capability_profile="chat_compatible_json"),
        sdk_client=_FakeSDK(chat_api=chat_api),
    )

    response = client.request_operator_decision(
        system_prompt="system prompt",
        user_prompt="user prompt",
        candidate_operator_ids=("native_sbx_pm", "hot_pair_to_sink", "radiator_expand"),
    )

    assert response.selected_operator_id == "hot_pair_to_sink"
    assert response.raw_payload["selected_operator_id"] == "hot_pair_to_sink"


def test_chat_compatible_json_client_retries_invalid_operator_id_before_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ":"}',
            '{"selected_operator_id": "radiator_expand"}',
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
        candidate_operator_ids=("native_sbx_pm", "radiator_expand"),
    )

    assert response.selected_operator_id == "radiator_expand"
    assert chat_api.call_count == 2


def test_request_operator_decision_records_attempt_trace_for_retry_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ":"}',
            '{"selected_operator_id": "radiator_expand"}',
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
        candidate_operator_ids=("native_sbx_pm", "radiator_expand"),
        attempt_trace=attempt_trace,
    )

    assert response.selected_operator_id == "radiator_expand"
    assert len(attempt_trace) == 2
    assert attempt_trace[0]["valid"] is False
    assert "outside the requested operator registry" in str(attempt_trace[0]["error"])
    assert attempt_trace[1]["valid"] is True
    assert attempt_trace[1]["selected_operator_id"] == "radiator_expand"


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
            candidate_operator_ids=("native_sbx_pm", "radiator_expand"),
        )

    assert chat_api.call_count == 2


def test_chat_compatible_json_client_strengthens_retry_prompt_after_invalid_operator_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "test-key")
    chat_api = _FakeChatCompletionsAPI(
        [
            '{"selected_operator_id": ""}',
            '{"selected_operator_id": "radiator_expand"}',
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
        candidate_operator_ids=("native_sbx_pm", "radiator_expand"),
    )

    assert chat_api.last_kwargs is not None
    retry_system_prompt = str(chat_api.last_kwargs["messages"][0]["content"])
    assert "previous response was invalid" in retry_system_prompt.lower()
    assert "radiator_expand" in retry_system_prompt


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
