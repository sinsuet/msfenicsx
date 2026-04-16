"""Content-addressed prompt markdown store (sha1 of body)."""

from __future__ import annotations

from pathlib import Path


def test_store_prompt_deduplicates_identical_bodies(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    body = "# System\n\nYou are a helpful operator controller.\n"

    ref1 = store.store(kind="request", body=body, model="gpt-5.4", decision_id="g000-e0001-d00")
    ref2 = store.store(kind="request", body=body, model="gpt-5.4", decision_id="g000-e0002-d00")

    assert ref1 == ref2
    md_files = sorted((tmp_path / "prompts").glob("*.md"))
    assert len(md_files) == 1


def test_store_prompt_different_bodies_produce_different_refs(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    ref_a = store.store(kind="request", body="abc", model="gpt-5.4", decision_id="g000-e0000-d00")
    ref_b = store.store(kind="request", body="xyz", model="gpt-5.4", decision_id="g000-e0001-d00")

    assert ref_a != ref_b


def test_stored_markdown_has_yaml_frontmatter(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    ref = store.store(
        kind="response",
        body="OK.",
        model="gpt-5.4",
        decision_id="g005-e0042-d01",
    )
    content = (tmp_path / ref).read_text(encoding="utf-8")
    # YAML frontmatter between triple-dash markers.
    assert content.startswith("---\n")
    assert "\n---\n" in content[4:]
    assert "kind: response" in content
    assert "sha1:" in content
    assert "model: gpt-5.4" in content
    assert "g005-e0042-d01" in content


def test_store_prompt_extends_decision_ids_on_dedup(tmp_path: Path) -> None:
    from optimizers.traces.prompt_store import PromptStore

    store = PromptStore(tmp_path / "prompts")
    body = "shared body"
    store.store(kind="request", body=body, model="m", decision_id="g000-e0001-d00")
    store.store(kind="request", body=body, model="m", decision_id="g000-e0002-d00")

    md_files = list((tmp_path / "prompts").glob("*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text(encoding="utf-8")
    assert "g000-e0001-d00" in content
    assert "g000-e0002-d00" in content
