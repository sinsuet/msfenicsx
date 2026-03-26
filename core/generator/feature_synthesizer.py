"""Synthesize non-component thermal boundary features."""

from __future__ import annotations

from typing import Any


def synthesize_boundary_features(sampled_boundary_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    synthesized: list[dict[str, Any]] = []
    for index, feature in enumerate(sampled_boundary_features, start=1):
        synthesized.append(
            {
                "feature_id": f"{feature['family_id']}-{index:03d}",
                "kind": feature["kind"],
                "edge": feature["edge"],
                "start": feature["start"],
                "end": feature["end"],
                "sink_temperature": feature["sink_temperature"],
                "transfer_coefficient": feature["transfer_coefficient"],
            }
        )
    return synthesized
