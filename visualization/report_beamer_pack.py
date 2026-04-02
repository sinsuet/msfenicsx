"""Render a Beamer-friendly figure pack for the 2026-04-01 progress reports."""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs/reports/figures/2026-04-01-beamer-pack"
TEMPLATE_PATH = REPO_ROOT / "scenarios/templates/panel_four_component_hot_cold_benchmark.yaml"
EVALUATION_SPEC_PATH = REPO_ROOT / "scenarios/evaluation/panel_four_component_hot_cold_baseline.yaml"
OPTIMIZATION_SPEC_PATH = REPO_ROOT / "scenarios/optimization/panel_four_component_hot_cold_nsga2_b0.yaml"

MODE_ORDER = ["raw", "union", "llm"]
MODE_LABELS = {"raw": "Raw NSGA-II", "union": "Union-uniform", "llm": "LLM-union"}
MODE_COLORS = {"raw": "#3B6FB6", "union": "#D98E32", "llm": "#2D936C"}
COMPONENT_LABELS = {"processor": "处理器", "rf_power_amp": "功放", "obc": "OBC", "battery_pack": "电池"}
COMPONENT_COLORS = {"processor": "#C44E52", "rf_power_amp": "#E39D3E", "obc": "#7A8E99", "battery_pack": "#4E79A7"}
OPERATOR_LABELS = {
    "native_sbx_pm": "原生 SBX+PM",
    "sbx_pm_global": "全局 SBX+PM",
    "local_refine": "局部微调",
    "hot_pair_to_sink": "热源靠散热器",
    "hot_pair_separate": "热源分离",
    "battery_to_warm_zone": "电池靠暖区",
    "radiator_align_hot_pair": "散热器对齐热源",
    "radiator_expand": "散热器扩展",
    "radiator_contract": "散热器收缩",
}
RUN_SPECS: dict[str, dict[str, Any]] = {
    "seed23": {
        "seed": 23,
        "base_case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-23-real-test/representatives/knee-candidate/cases/hot.yaml",
        "modes": {
            "raw": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-23-real-test/optimization_result.json",
                "representative_label": "knee_candidate",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-23-real-test/representatives/knee-candidate/cases/hot.yaml",
            },
            "union": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/optimization_result.json",
                "representative_label": "min_hot_pa_peak",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/representatives/min-hot-pa-peak/cases/hot.yaml",
                "operator_trace_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-23-real-test/operator_trace.json",
            },
            "llm": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/optimization_result.json",
                "representative_label": "knee_candidate",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/representatives/knee-candidate/cases/hot.yaml",
                "operator_trace_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/operator_trace.json",
                "llm_metrics_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-window-guardrail-multiseed/seed-23-real-test/llm_metrics.json",
            },
        },
    },
    "seed17": {
        "seed": 17,
        "base_case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-17-real-test/representatives/knee-candidate/cases/hot.yaml",
        "modes": {
            "raw": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-17-real-test/optimization_result.json",
                "representative_label": "knee_candidate",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-raw-multiseed/seed-17-real-test/representatives/knee-candidate/cases/hot.yaml",
            },
            "union": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-17-real-test/optimization_result.json",
                "representative_label": "knee_candidate",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-17-real-test/representatives/knee-candidate/cases/hot.yaml",
                "operator_trace_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-uniform-multiseed/seed-17-real-test/operator_trace.json",
            },
            "llm": {
                "result_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/optimization_result.json",
                "representative_label": "knee_candidate",
                "case_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/representatives/knee-candidate/cases/hot.yaml",
                "operator_trace_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/operator_trace.json",
                "llm_metrics_path": REPO_ROOT / "scenario_runs/optimizations/panel-four-component-hot-cold-nsga2-union-llm-l1-gpt54-full/2026-04-01-kernel-validation-seed17/llm_metrics.json",
            },
        },
    },
}


def _configure_matplotlib() -> None:
    font_family = "DejaVu Sans"
    for path in [
        Path("/mnt/c/Windows/Fonts/msyh.ttc"),
        Path("/mnt/c/Windows/Fonts/msyhbd.ttc"),
        Path("/mnt/c/Windows/Fonts/simhei.ttf"),
        Path("/mnt/c/Windows/Fonts/simsun.ttc"),
    ]:
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            font_family = font_manager.FontProperties(fname=str(path)).get_name()
            break
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font_family, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.facecolor": "#F6F2EB",
            "axes.facecolor": "#F6F2EB",
            "savefig.facecolor": "#F6F2EB",
            "font.size": 12,
            "axes.titleweight": "bold",
        }
    )


_configure_matplotlib()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def count_operator_usage(path: Path) -> dict[str, int]:
    rows = load_json(path)
    counts = Counter(row["operator_id"] for row in rows)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _apply_decision_vector_to_case(case_payload: dict[str, Any], decision_vector: dict[str, float]) -> dict[str, Any]:
    case_copy = copy.deepcopy(case_payload)
    for component in case_copy["components"]:
        role = component["role"]
        if role == "processor":
            component["pose"]["x"] = float(decision_vector["processor_x"])
            component["pose"]["y"] = float(decision_vector["processor_y"])
        elif role == "rf_power_amp":
            component["pose"]["x"] = float(decision_vector["rf_power_amp_x"])
            component["pose"]["y"] = float(decision_vector["rf_power_amp_y"])
        elif role == "battery_pack":
            component["pose"]["x"] = float(decision_vector["battery_pack_x"])
            component["pose"]["y"] = float(decision_vector["battery_pack_y"])
    case_copy["boundary_features"][0]["start"] = float(decision_vector["radiator_start"])
    case_copy["boundary_features"][0]["end"] = float(decision_vector["radiator_end"])
    return case_copy


def _component_center(component: dict[str, Any]) -> tuple[float, float]:
    return float(component["pose"]["x"]), float(component["pose"]["y"])


def _component_rect(component: dict[str, Any]) -> tuple[float, float, float, float]:
    width = float(component["geometry"]["width"])
    height = float(component["geometry"]["height"])
    center_x, center_y = _component_center(component)
    return center_x - width / 2.0, center_y - height / 2.0, width, height


def _extract_seed_context(seed_key: str, seed_spec: dict[str, Any]) -> dict[str, Any]:
    base_case = load_yaml(seed_spec["base_case_path"])
    initial_vector: dict[str, float] | None = None
    modes: dict[str, Any] = {}
    operator_counts: dict[str, dict[str, int]] = {}
    llm_metrics: dict[str, Any] = {}
    for mode_key, mode_spec in seed_spec["modes"].items():
        result_payload = load_json(mode_spec["result_path"])
        history = result_payload["history"]
        mode_initial_vector = history[0]["decision_vector"]
        if initial_vector is None:
            initial_vector = mode_initial_vector
        elif initial_vector != mode_initial_vector:
            raise ValueError(f"{seed_key} has inconsistent initial vectors")
        representative_label = mode_spec["representative_label"]
        modes[mode_key] = {
            "aggregate": result_payload["aggregate_metrics"],
            "feasible_count": sum(1 for row in history if row["feasible"]),
            "history": history,
            "representative_label": representative_label,
            "representative": result_payload["representative_candidates"][representative_label],
            "case": load_yaml(mode_spec["case_path"]),
        }
        if "operator_trace_path" in mode_spec:
            operator_counts[mode_key] = count_operator_usage(mode_spec["operator_trace_path"])
        if "llm_metrics_path" in mode_spec:
            llm_metrics[mode_key] = load_json(mode_spec["llm_metrics_path"])
    if initial_vector is None:
        raise ValueError(f"missing initial vector for {seed_key}")
    return {
        "seed": seed_spec["seed"],
        "base_case": base_case,
        "initial_case": _apply_decision_vector_to_case(base_case, initial_vector),
        "initial_decision_vector": initial_vector,
        "modes": modes,
        "operator_counts": operator_counts,
        "llm_metrics": llm_metrics,
    }


def build_beamer_pack_context() -> dict[str, Any]:
    return {
        "repo_root": REPO_ROOT,
        "template": load_yaml(TEMPLATE_PATH),
        "evaluation_spec": load_yaml(EVALUATION_SPEC_PATH),
        "optimization_spec": load_yaml(OPTIMIZATION_SPEC_PATH),
        "seeds": {seed_key: _extract_seed_context(seed_key, seed_spec) for seed_key, seed_spec in RUN_SPECS.items()},
    }


def _save_figure(fig: plt.Figure, stem: str, output_dir: Path, *, include_pdf: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    png_path = output_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    outputs.append(png_path)
    if include_pdf:
        pdf_path = output_dir / f"{stem}.pdf"
        fig.savefig(pdf_path, bbox_inches="tight")
        outputs.append(pdf_path)
    plt.close(fig)
    return outputs


def _add_box(ax: plt.Axes, x: float, y: float, width: float, height: float, *, title: str, lines: list[str], facecolor: str = "#FFF9F0") -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.018,rounding_size=0.02",
            linewidth=1.2,
            edgecolor="#D5C6B2",
            facecolor=facecolor,
            transform=ax.transAxes,
        )
    )
    ax.text(x + 0.02, y + height - 0.07, title, transform=ax.transAxes, fontsize=15, fontweight="bold", va="top")
    for index, line in enumerate(lines):
        ax.text(x + 0.02, y + height - 0.14 - index * 0.075, line, transform=ax.transAxes, fontsize=11, va="top", color="#425466")


def _draw_panel_layout(
    ax: plt.Axes,
    *,
    template: dict[str, Any],
    case_payload: dict[str, Any],
    title: str,
    subtitle: str | None = None,
    show_region_labels: bool = True,
    show_component_labels: bool = True,
) -> None:
    panel_width = float(case_payload["panel_domain"]["width"])
    panel_height = float(case_payload["panel_domain"]["height"])
    placement_region = template["placement_regions"][0]
    keep_out_region = template["keep_out_regions"][0]
    ax.set_xlim(0.0, panel_width)
    ax.set_ylim(0.0, panel_height)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0.0, 0.0), panel_width, panel_height, facecolor="#F2EBDD", edgecolor="#8B7D6B", linewidth=2.2))
    ax.add_patch(Rectangle((placement_region["x_min"], placement_region["y_min"]), placement_region["x_max"] - placement_region["x_min"], placement_region["y_max"] - placement_region["y_min"], facecolor="#F8F5ED", edgecolor="#C7B89E", linewidth=1.2, linestyle="--"))
    ax.add_patch(Rectangle((keep_out_region["x_min"], keep_out_region["y_min"]), keep_out_region["x_max"] - keep_out_region["x_min"], keep_out_region["y_max"] - keep_out_region["y_min"], facecolor="#E9E1D2", edgecolor="#C9B89D", linewidth=1.0, alpha=0.9))
    radiator = case_payload["boundary_features"][0]
    ax.plot([float(radiator["start"]), float(radiator["end"])], [panel_height, panel_height], color="#208A77", linewidth=7, solid_capstyle="round", zorder=5)
    ax.plot([float(radiator["start"]), float(radiator["end"])], [panel_height, panel_height], "o", color="#208A77", markersize=5, zorder=6)
    for component in case_payload["components"]:
        x0, y0, width, height = _component_rect(component)
        role = component["role"]
        ax.add_patch(Rectangle((x0, y0), width, height, facecolor=COMPONENT_COLORS[role], edgecolor="white", linewidth=2.0, zorder=10))
        if show_component_labels:
            ax.text(x0 + width / 2.0, y0 + height / 2.0, COMPONENT_LABELS[role], ha="center", va="center", fontsize=11, color="white", fontweight="bold", zorder=11)
    if show_region_labels:
        ax.text(0.06, 0.08, "面板域 1.0 x 0.8", fontsize=11, color="#556270")
        ax.text(placement_region["x_min"] + 0.01, placement_region["y_max"] - 0.02, "主放置区域", fontsize=11, color="#7A6648", va="top")
        ax.text(0.02, keep_out_region["y_min"] + 0.02, "顶部禁布条", fontsize=10, color="#7A6648", va="bottom")
        ax.text(float(radiator["start"]), panel_height - 0.05, "顶部 radiator", fontsize=11, color="#0E6B5B", fontweight="bold")
    ax.set_title(title, fontsize=16, pad=12)
    if subtitle:
        ax.text(0.5, -0.09, subtitle, transform=ax.transAxes, ha="center", va="top", fontsize=10, color="#5A6775")


def _draw_metric_bars(ax: plt.Axes, *, values: dict[str, float], title: str, value_fmt: str, better_note: str) -> None:
    labels = [MODE_LABELS[mode_key] for mode_key in MODE_ORDER]
    heights = [values[mode_key] for mode_key in MODE_ORDER]
    bars = ax.bar(range(len(MODE_ORDER)), heights, color=[MODE_COLORS[mode_key] for mode_key in MODE_ORDER], width=0.62)
    ax.set_xticks(range(len(MODE_ORDER)), labels)
    ax.set_title(f"{title}\n{better_note}", fontsize=14)
    ax.grid(axis="y", linestyle=":", alpha=0.35)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, height in zip(bars, heights, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2.0, height, value_fmt.format(height), ha="center", va="bottom", fontsize=11)


def _build_objective_values(mode_payload: dict[str, Any]) -> dict[str, float]:
    objectives = mode_payload["representative"]["objective_values"]
    return {"hot_pa": float(objectives["minimize_hot_pa_peak"]), "cold_battery": float(objectives["maximize_cold_battery_min"]), "radiator": float(objectives["minimize_radiator_resource"])}


def _draw_objective_dotplot(ax: plt.Axes, *, title: str, values: dict[str, float], better_note: str) -> None:
    xs = list(range(len(MODE_ORDER)))
    ys = [values[mode_key] for mode_key in MODE_ORDER]
    ax.scatter(xs, ys, s=210, color=[MODE_COLORS[mode_key] for mode_key in MODE_ORDER], edgecolors="white", linewidths=1.8, zorder=5)
    ax.plot(xs, ys, color="#B3A18A", linestyle="--", linewidth=1.4, zorder=2)
    margin = max((max(ys) - min(ys)) * 0.35, 0.02)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_xticks(xs, [MODE_LABELS[mode_key] for mode_key in MODE_ORDER])
    ax.set_title(f"{title}\n{better_note}", fontsize=14)
    ax.grid(axis="y", linestyle=":", alpha=0.35)
    ax.spines[["top", "right"]].set_visible(False)
    for x_pos, y_value in zip(xs, ys, strict=True):
        ax.text(x_pos, y_value, f"  {y_value:.4f}", fontsize=11, va="bottom")


def _layout_subtitle(mode_payload: dict[str, Any]) -> str:
    objectives = mode_payload["representative"]["objective_values"]
    return f"eval {mode_payload['representative']['evaluation_index']} | hot PA {objectives['minimize_hot_pa_peak']:.3f} | cold battery {objectives['maximize_cold_battery_min']:.3f} | radiator {objectives['minimize_radiator_resource']:.3f}"


def _best_value(values: dict[str, float], *, higher_is_better: bool) -> float:
    return max(values.values()) if higher_is_better else min(values.values())


def _render_01_benchmark_layout_overview(context: dict[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(16, 9))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.1, 1.0])
    ax_layout = fig.add_subplot(gs[0, 0])
    ax_info = fig.add_subplot(gs[0, 1])
    ax_info.axis("off")

    template = context["template"]
    case_payload = context["seeds"]["seed23"]["modes"]["raw"]["case"]
    _draw_panel_layout(
        ax_layout,
        template=template,
        case_payload=case_payload,
        title="主线 benchmark 布局总览",
        subtitle="示意采用 seed-23 的真实几何实例；区域约束来自模板",
    )

    processor_family = next(family for family in template["component_families"] if family["family_id"] == "processor")
    pa_family = next(family for family in template["component_families"] if family["family_id"] == "rf_power_amp")
    obc_family = next(family for family in template["component_families"] if family["family_id"] == "obc")
    battery_family = next(family for family in template["component_families"] if family["family_id"] == "battery_pack")
    hot_case = next(case for case in template["operating_case_profiles"] if case["operating_case_id"] == "hot")
    cold_case = next(case for case in template["operating_case_profiles"] if case["operating_case_id"] == "cold")

    _add_box(
        ax_info,
        0.02,
        0.70,
        0.94,
        0.22,
        title="场景与区域",
        lines=[
            "面板域: 1.0 x 0.8",
            "主放置区: x in [0.05, 0.95], y in [0.05, 0.72]",
            "顶部禁布条: y in [0.74, 0.80]; 顶边 radiator span: [0.25, 0.75]",
        ],
    )
    _add_box(
        ax_info,
        0.02,
        0.35,
        0.94,
        0.27,
        title="组件族与尺寸范围",
        lines=[
            f"处理器: {processor_family['geometry']['width']['min']:.2f}-{processor_family['geometry']['width']['max']:.2f} x {processor_family['geometry']['height']['min']:.2f}-{processor_family['geometry']['height']['max']:.2f}",
            f"功放: {pa_family['geometry']['width']['min']:.2f}-{pa_family['geometry']['width']['max']:.2f} x {pa_family['geometry']['height']['min']:.2f}-{pa_family['geometry']['height']['max']:.2f}",
            f"OBC: {obc_family['geometry']['width']['min']:.2f}-{obc_family['geometry']['width']['max']:.2f} x {obc_family['geometry']['height']['min']:.2f}-{obc_family['geometry']['height']['max']:.2f}",
            f"电池: {battery_family['geometry']['width']['min']:.2f}-{battery_family['geometry']['width']['max']:.2f} x {battery_family['geometry']['height']['min']:.2f}-{battery_family['geometry']['height']['max']:.2f}",
        ],
    )
    _add_box(
        ax_info,
        0.02,
        0.05,
        0.45,
        0.23,
        title="Hot 工况",
        lines=[
            f"环境温度: {hot_case['ambient_temperature']:.0f} K",
            "功率 96 / 80 / 20 / 4; sink 305 K, h = 4",
        ],
        facecolor="#FFF3EE",
    )
    _add_box(
        ax_info,
        0.51,
        0.05,
        0.45,
        0.23,
        title="Cold 工况",
        lines=[
            f"环境温度: {cold_case['ambient_temperature']:.0f} K",
            "功率 32 / 24 / 8 / 1; sink 248 K, h = 10",
        ],
        facecolor="#EEF7FF",
    )
    fig.suptitle("01  主线热布局 benchmark 场景", fontsize=24, fontweight="bold", y=0.98)
    return fig


def _render_02_design_variables_schematic(context: dict[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(16, 9))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.12, 0.88])
    ax_layout = fig.add_subplot(gs[0, 0])
    ax_info = fig.add_subplot(gs[0, 1])
    ax_info.axis("off")

    template = context["template"]
    case_payload = context["seeds"]["seed23"]["modes"]["raw"]["case"]
    _draw_panel_layout(
        ax_layout,
        template=template,
        case_payload=case_payload,
        title="8 维设计变量示意",
        subtitle="位置变量只作用于 processor / PA / battery；OBC 固定为 benchmark seed 实例",
        show_region_labels=False,
    )

    role_to_component = {component["role"]: component for component in case_payload["components"]}
    for role, label, text_xy in [
        ("processor", "processor_x / processor_y", (0.08, 0.18)),
        ("rf_power_amp", "rf_power_amp_x / rf_power_amp_y", (0.70, 0.15)),
        ("battery_pack", "battery_pack_x / battery_pack_y", (0.73, 0.57)),
    ]:
        center = _component_center(role_to_component[role])
        ax_layout.add_patch(FancyArrowPatch(text_xy, center, arrowstyle="->", mutation_scale=14, linewidth=2.0, color="#4A5B6A"))
        ax_layout.text(text_xy[0], text_xy[1], label, fontsize=11, color="#33424F", bbox={"boxstyle": "round,pad=0.25", "fc": "#FFF9F0", "ec": "#D8C8B1"})

    radiator = case_payload["boundary_features"][0]
    for x_pos, label, alignment in [
        (float(radiator["start"]), "radiator_start", "right"),
        (float(radiator["end"]), "radiator_end", "left"),
    ]:
        ax_layout.plot([x_pos, x_pos], [0.74, 0.83], linestyle=":", linewidth=2.0, color="#208A77")
        ax_layout.text(x_pos, 0.71, label, fontsize=10, color="#0E6B5B", ha=alignment, bbox={"boxstyle": "round,pad=0.2", "fc": "#EEF8F6", "ec": "#B9E0D7"})

    obc_center = _component_center(role_to_component["obc"])
    ax_layout.text(obc_center[0] + 0.11, obc_center[1] - 0.08, "OBC pose 固定\n不进入优化变量", fontsize=11, color="#445566", bbox={"boxstyle": "round,pad=0.3", "fc": "#F1F4F6", "ec": "#CBD6DD"})

    _add_box(
        ax_info,
        0.02,
        0.58,
        0.94,
        0.32,
        title="当前决策编码",
        lines=[
            "三个可移动组件各含 (x, y)",
            "processor / rf_power_amp / battery_pack",
            "radiator: (radiator_start, radiator_end)",
        ],
    )
    _add_box(ax_info, 0.02, 0.30, 0.94, 0.23, title="关键解释", lines=["三种方法共享同一 8D decision space", "union/llm 只改 proposal/control"], facecolor="#EEF7FF")
    _add_box(ax_info, 0.02, 0.03, 0.94, 0.23, title="约束接口", lines=["统一进入 repair -> hot/cold solve -> evaluation", "survival 语义保持不变"], facecolor="#FFF3EE")
    fig.suptitle("02  8 维设计变量与固定组件关系", fontsize=24, fontweight="bold", y=0.98)
    return fig


def _lane_box(ax: plt.Axes, x: float, y: float, w: float, h: float, text: str, *, facecolor: str) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02", linewidth=1.3, edgecolor="#C9B8A0", facecolor=facecolor))
    ax.text(x + w / 2.0, y + h / 2.0, text, ha="center", va="center", fontsize=12, fontweight="bold")


def _render_03_raw_union_llm_architecture(context: dict[str, Any]) -> plt.Figure:
    _ = context
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    lane_y = {"raw": 0.69, "union": 0.43, "llm": 0.17}
    x_positions = [0.12, 0.31, 0.54, 0.76, 0.91]
    box_width = [0.14, 0.18, 0.15, 0.15, 0.08]
    box_height = 0.14
    shared_steps = ["8D 变量编码", "", "repair", "hot/cold\n求解与评价", "survival /\nPareto"]
    proposal_text = {
        "raw": "原生 SBX + PM\n无控制器",
        "union": "mixed action registry\nuniform controller",
        "llm": "mixed action registry\nLLM controller",
    }
    for mode_key in MODE_ORDER:
        y_pos = lane_y[mode_key]
        ax.text(0.015, y_pos + 0.06, MODE_LABELS[mode_key], fontsize=15, fontweight="bold", color=MODE_COLORS[mode_key], va="center")
        texts = shared_steps.copy()
        texts[1] = proposal_text[mode_key]
        lane_colors = {0: "#F5F0E7", 1: "#EEF7FF" if mode_key == "raw" else ("#FFF6E9" if mode_key == "union" else "#ECF9F2"), 2: "#F5F0E7", 3: "#F5F0E7", 4: "#F5F0E7"}
        for index, (x_pos, width) in enumerate(zip(x_positions, box_width, strict=True)):
            _lane_box(ax, x_pos, y_pos, width, box_height, texts[index], facecolor=lane_colors[index])
            if index < len(x_positions) - 1:
                ax.add_patch(FancyArrowPatch((x_pos + width, y_pos + box_height / 2.0), (x_positions[index + 1], y_pos + box_height / 2.0), arrowstyle="->", mutation_scale=16, linewidth=1.8, color="#6A7885"))
    ax.text(0.5, 0.95, "03  Raw / Union / LLM-union 架构关系", ha="center", va="center", fontsize=24, fontweight="bold")
    ax.text(0.5, 0.89, "共享 benchmark、8D 编码、repair、热求解、evaluation 与 survival；只替换 proposal/control 层", ha="center", va="center", fontsize=13, color="#596877")
    ax.add_patch(Rectangle((0.02, 0.11), 0.96, 0.76, linewidth=1.1, edgecolor="#D7CAB6", facecolor="none", linestyle="--"))
    ax.text(0.74, 0.08, "action-space expansion != decision-space expansion", fontsize=12, color="#7A6648", fontweight="bold")
    return fig


def _render_04_seed23_initial_and_final_layouts(context: dict[str, Any]) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    seed_context = context["seeds"]["seed23"]
    template = context["template"]
    _draw_panel_layout(axes[0, 0], template=template, case_payload=seed_context["initial_case"], title="共同初始布局", subtitle="seed-23, eval 1, 三种方法共享同一初始解")
    _draw_panel_layout(axes[0, 1], template=template, case_payload=seed_context["modes"]["raw"]["case"], title="Raw NSGA-II 最终代表解", subtitle=_layout_subtitle(seed_context["modes"]["raw"]))
    _draw_panel_layout(axes[1, 0], template=template, case_payload=seed_context["modes"]["union"]["case"], title="Union-uniform 最终代表解", subtitle=_layout_subtitle(seed_context["modes"]["union"]))
    _draw_panel_layout(axes[1, 1], template=template, case_payload=seed_context["modes"]["llm"]["case"], title="LLM-union 最终代表解", subtitle=_layout_subtitle(seed_context["modes"]["llm"]))
    fig.subplots_adjust(hspace=0.30, wspace=0.22, top=0.90, bottom=0.08)
    fig.suptitle("04  Seed-23 从共同初始布局到三种终态", fontsize=24, fontweight="bold", y=0.98)
    return fig


def _render_05_seed23_metrics_comparison(context: dict[str, Any]) -> plt.Figure:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    seed_context = context["seeds"]["seed23"]
    feasible_rate = {mode_key: seed_context["modes"][mode_key]["aggregate"]["feasible_rate"] * 100.0 for mode_key in MODE_ORDER}
    feasible_count = {mode_key: float(seed_context["modes"][mode_key]["feasible_count"]) for mode_key in MODE_ORDER}
    first_feasible = {mode_key: float(seed_context["modes"][mode_key]["aggregate"]["first_feasible_eval"]) for mode_key in MODE_ORDER}
    pareto_size = {mode_key: float(seed_context["modes"][mode_key]["aggregate"]["pareto_size"]) for mode_key in MODE_ORDER}
    _draw_metric_bars(axes[0, 0], values=feasible_rate, title="可行解比例 (%)", value_fmt="{:.2f}", better_note="越高越好")
    _draw_metric_bars(axes[0, 1], values=feasible_count, title="可行解数量", value_fmt="{:.0f}", better_note="越高越好")
    _draw_metric_bars(axes[1, 0], values=first_feasible, title="首次进入可行域评估", value_fmt="{:.0f}", better_note="越低越好")
    _draw_metric_bars(axes[1, 1], values=pareto_size, title="Pareto 前沿规模", value_fmt="{:.0f}", better_note="越高越好")
    fig.suptitle("05  Seed-23 三种方法的聚合实验指标", fontsize=24, fontweight="bold", y=0.98)
    return fig


def _render_06_seed23_representative_objectives(context: dict[str, Any]) -> plt.Figure:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.8))
    seed_context = context["seeds"]["seed23"]
    objective_payloads = {mode_key: _build_objective_values(seed_context["modes"][mode_key]) for mode_key in MODE_ORDER}
    _draw_objective_dotplot(axes[0], title="Hot 功放峰值温度", values={mode_key: objective_payloads[mode_key]["hot_pa"] for mode_key in MODE_ORDER}, better_note="越低越好")
    _draw_objective_dotplot(axes[1], title="Cold 电池最低温度", values={mode_key: objective_payloads[mode_key]["cold_battery"] for mode_key in MODE_ORDER}, better_note="越高越好")
    _draw_objective_dotplot(axes[2], title="Radiator 资源占用", values={mode_key: objective_payloads[mode_key]["radiator"] for mode_key in MODE_ORDER}, better_note="越低越好")
    fig.suptitle("06  Seed-23 代表点三目标对比", fontsize=24, fontweight="bold", y=1.02)
    fig.text(0.5, -0.02, "注：raw 与 llm 使用 knee candidate；union-uniform 使用 min hot PA representative。", ha="center", fontsize=11, color="#5A6775")
    return fig


def _render_07_seed23_operator_mix(context: dict[str, Any]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(16, 8.5))
    seed_context = context["seeds"]["seed23"]
    union_counts = seed_context["operator_counts"]["union"]
    llm_counts = seed_context["operator_counts"]["llm"]
    operator_ids = sorted(set(union_counts) | set(llm_counts), key=lambda key: -(union_counts.get(key, 0) + llm_counts.get(key, 0)))
    y_positions = list(range(len(operator_ids)))
    ax.barh([y - 0.18 for y in y_positions], [union_counts.get(key, 0) for key in operator_ids], height=0.34, color=MODE_COLORS["union"], label="Union-uniform")
    ax.barh([y + 0.18 for y in y_positions], [llm_counts.get(key, 0) for key in operator_ids], height=0.34, color=MODE_COLORS["llm"], label="LLM-union")
    ax.set_yticks(y_positions, [OPERATOR_LABELS.get(operator_id, operator_id) for operator_id in operator_ids])
    ax.invert_yaxis()
    ax.grid(axis="x", linestyle=":", alpha=0.35)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right")
    ax.set_title("07  Seed-23 Operator Mix 对比\nraw 不包含 operator pool，因此不在本图中", fontsize=22, pad=18)
    ax.set_xlabel("选择次数")
    for y_pos, operator_id in enumerate(operator_ids):
        union_value = union_counts.get(operator_id, 0)
        llm_value = llm_counts.get(operator_id, 0)
        ax.text(union_value + 0.5, y_pos - 0.18, str(union_value), va="center", fontsize=10, color="#6A4B16")
        ax.text(llm_value + 0.5, y_pos + 0.18, str(llm_value), va="center", fontsize=10, color="#1F5F46")
    return fig


def _render_08_seed17_best_snapshot(context: dict[str, Any]) -> plt.Figure:
    fig = plt.figure(figsize=(16, 10.8))
    gs = GridSpec(2, 3, figure=fig, height_ratios=[1.05, 0.78])
    seed_context = context["seeds"]["seed17"]
    template = context["template"]
    for index, mode_key in enumerate(MODE_ORDER):
        ax = fig.add_subplot(gs[0, index])
        _draw_panel_layout(ax, template=template, case_payload=seed_context["modes"][mode_key]["case"], title=f"{MODE_LABELS[mode_key]} 终态", subtitle=_layout_subtitle(seed_context["modes"][mode_key]))

    ax_table = fig.add_subplot(gs[1, :])
    ax_table.axis("off")
    rows = [
        ("可行解比例", {mode_key: seed_context["modes"][mode_key]["aggregate"]["feasible_rate"] * 100.0 for mode_key in MODE_ORDER}, True, "{:.2f}%"),
        ("可行解数量", {mode_key: float(seed_context["modes"][mode_key]["feasible_count"]) for mode_key in MODE_ORDER}, True, "{:.0f}"),
        ("首次进入可行域", {mode_key: float(seed_context["modes"][mode_key]["aggregate"]["first_feasible_eval"]) for mode_key in MODE_ORDER}, False, "{:.0f}"),
        ("Pareto 规模", {mode_key: float(seed_context["modes"][mode_key]["aggregate"]["pareto_size"]) for mode_key in MODE_ORDER}, True, "{:.0f}"),
        ("hot PA", {mode_key: _build_objective_values(seed_context["modes"][mode_key])["hot_pa"] for mode_key in MODE_ORDER}, False, "{:.4f}"),
        ("cold battery", {mode_key: _build_objective_values(seed_context["modes"][mode_key])["cold_battery"] for mode_key in MODE_ORDER}, True, "{:.4f}"),
        ("radiator", {mode_key: _build_objective_values(seed_context["modes"][mode_key])["radiator"] for mode_key in MODE_ORDER}, False, "{:.4f}"),
    ]
    ax_table.add_patch(FancyBboxPatch((0.01, 0.03), 0.98, 0.9, boxstyle="round,pad=0.02,rounding_size=0.02", linewidth=1.3, edgecolor="#D7CAB6", facecolor="#FFF9F0", transform=ax_table.transAxes))
    ax_table.text(0.03, 0.88, "关键指标总表", transform=ax_table.transAxes, fontsize=18, fontweight="bold")
    header_x = {"metric": 0.05, "raw": 0.37, "union": 0.60, "llm": 0.82}
    ax_table.text(header_x["metric"], 0.78, "指标", transform=ax_table.transAxes, fontsize=13, fontweight="bold")
    for mode_key in MODE_ORDER:
        ax_table.text(header_x[mode_key], 0.78, MODE_LABELS[mode_key], transform=ax_table.transAxes, fontsize=13, fontweight="bold", ha="center", color=MODE_COLORS[mode_key])
    for row_index, (row_label, values, higher_is_better, fmt) in enumerate(rows):
        y_pos = 0.69 - row_index * 0.09
        best = _best_value(values, higher_is_better=higher_is_better)
        ax_table.text(header_x["metric"], y_pos, row_label, transform=ax_table.transAxes, fontsize=12)
        for mode_key in MODE_ORDER:
            ax_table.text(header_x[mode_key], y_pos, fmt.format(values[mode_key]), transform=ax_table.transAxes, fontsize=12, ha="center", color=MODE_COLORS[mode_key] if values[mode_key] == best else "#425466", fontweight="bold" if values[mode_key] == best else "normal")
    llm_metrics = seed_context["llm_metrics"]["llm"]
    ax_table.text(0.03, 0.08, f"LLM 运行代价: requests={llm_metrics['request_count']}, avg latency={llm_metrics['elapsed_seconds_avg']:.2f}s, fallback={llm_metrics['fallback_count']}", transform=ax_table.transAxes, fontsize=11, color="#4A5B6A")
    fig.suptitle("08  Seed-17 最佳快照：终态布局与关键指标", fontsize=24, fontweight="bold", y=0.98)
    return fig


def render_beamer_pack(*, output_dir: Path | None = None, include_pdf: bool = True) -> list[Path]:
    context = build_beamer_pack_context()
    target_dir = output_dir or DEFAULT_OUTPUT_DIR
    figures = [
        ("01_benchmark_layout_overview", _render_01_benchmark_layout_overview(context)),
        ("02_design_variables_schematic", _render_02_design_variables_schematic(context)),
        ("03_raw_union_llm_architecture", _render_03_raw_union_llm_architecture(context)),
        ("04_seed23_initial_and_final_layouts", _render_04_seed23_initial_and_final_layouts(context)),
        ("05_seed23_metrics_comparison", _render_05_seed23_metrics_comparison(context)),
        ("06_seed23_representative_objectives", _render_06_seed23_representative_objectives(context)),
        ("07_seed23_operator_mix", _render_07_seed23_operator_mix(context)),
        ("08_seed17_best_snapshot", _render_08_seed17_best_snapshot(context)),
    ]
    outputs: list[Path] = []
    for stem, fig in figures:
        outputs.extend(_save_figure(fig, stem, target_dir, include_pdf=include_pdf))
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the 2026-04-01 Beamer report figure pack.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--png-only", action="store_true", help="Skip PDF export and write PNG files only.")
    args = parser.parse_args(argv)
    outputs = render_beamer_pack(output_dir=args.output_dir, include_pdf=not args.png_only)
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
