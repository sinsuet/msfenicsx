from pathlib import Path

import yaml


def test_s1_typical_template_has_expected_shape() -> None:
    template_path = Path("scenarios/templates/s1_typical.yaml")
    payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    assert payload["template_meta"]["template_id"] == "s1_typical"
    assert len(payload["component_families"]) == 15
    assert payload["operating_case_profiles"] == []
