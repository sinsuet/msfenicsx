from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from runtime_config import load_dotenv_file


def test_load_dotenv_file_sets_missing_environment_variables(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("DASHSCOPE_API_KEY=test-key\nMODEL_NAME=qwen3.5-plus\n", encoding="utf-8")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    loaded = load_dotenv_file(env_path)

    assert loaded["DASHSCOPE_API_KEY"] == "test-key"
    assert os.environ["DASHSCOPE_API_KEY"] == "test-key"
    assert os.environ["MODEL_NAME"] == "qwen3.5-plus"


def test_load_dotenv_file_does_not_override_existing_environment_variables(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("DASHSCOPE_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "existing-key")

    load_dotenv_file(env_path)

    assert os.environ["DASHSCOPE_API_KEY"] == "existing-key"
