from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimization.variable_registry import build_current_case_variable_registry
from thermal_state import load_state

from .demo_summary import collect_demo_summary


ROOT = Path(__file__).resolve().parents[2]


def _load_or_build_summary(runs_root: Path) -> dict[str, Any]:
    summary_path = runs_root / "demo_summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    return collect_demo_summary(runs_root)


def _load_state_if_exists(path: Path):
    if not path.exists():
        return None
    return load_state(path)


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text_if_exists(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _fmt_float(value: Any, digits: int = 3) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value):.{digits}f}"


def _fmt_delta(value: Any, digits: int = 3) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value):+.{digits}f}"


def _clip_text(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def _include_graphic(path: Path | None, *, width: str, height: str = "0.42\\textheight") -> str:
    if path is not None and path.exists():
        return rf"\includegraphics[width={width}]{{{path.as_posix()}}}"
    return rf"\missingfigure{{{width}}}{{{height}}}"


def _path_label(path: str) -> str:
    mapping = {
        "materials.spreader_material.conductivity": "热扩展块导热率",
        "materials.base_material.conductivity": "底板导热率",
        "components.2.width": "热扩展块宽度",
        "components.2.height": "热扩展块高度",
        "components.2.x0": "热扩展块 x 位置",
        "components.2.y0": "热扩展块 y 位置",
        "heat_sources.0.value": "芯片热源",
    }
    return mapping.get(path, path)


def _short_change_list(paths: list[str]) -> str:
    if not paths:
        return "无"
    return " + ".join(_path_label(path) for path in paths)


def _validation_note(item: dict[str, Any]) -> str:
    if item.get("validation_status") == "invalid":
        reasons = item.get("validation_reasons", [])
        if not reasons:
            return "提案非法"
        reason = reasons[0]
        if "outside the current envelope" in reason or "outside the design domain" in reason:
            return "几何越界"
        if "must stay within" in reason:
            return "超出变量范围"
        if "step ratio" in reason:
            return "步长触边"
        return _latex_escape(reason[:30])

    delta = item.get("delta_chip_max")
    changed_paths = item.get("changed_paths", [])
    if isinstance(delta, (int, float)) and delta <= -1.0:
        return "显著降温"
    if isinstance(delta, (int, float)) and abs(delta) < 0.05:
        if "materials.base_material.conductivity" in changed_paths:
            return "改善有限"
        return "该杠杆较弱"
    if changed_paths == ["materials.base_material.conductivity"]:
        return "识别到底板瓶颈"
    return "合法单步更新"


def _format_effect(item: dict[str, Any]) -> str:
    before = item.get("chip_max_before")
    after = item.get("chip_max_after")
    delta = item.get("delta_chip_max")
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return f"{before:.2f} -> {after:.2f} ({delta:+.2f})"
    if isinstance(before, (int, float)):
        return f"当前 {before:.2f}"
    return "-"


def _build_variable_rows(categories: set[str]) -> str:
    rows = []
    for item in build_current_case_variable_registry():
        if item.category not in categories:
            continue
        rows.append(
            " & ".join(
                [
                    _latex_escape(item.label),
                    _latex_escape(item.path),
                    _latex_escape(item.category),
                    f"{item.min_value:g}--{item.max_value:g}",
                    _latex_escape(item.recommended_direction),
                ]
            )
            + r" \\"
        )
    return "\n".join(rows) if rows else r"\multicolumn{5}{c}{暂无变量} \\"


def _build_component_rows(state) -> str:
    if state is None:
        return r"\multicolumn{5}{c}{未找到 baseline state} \\"
    rows = []
    for component in state.components:
        conductivity = state.materials[component.material].conductivity
        rows.append(
            " & ".join(
                [
                    _latex_escape(component.name),
                    f"({component.x0:.2f}, {component.y0:.2f})",
                    f"{component.width:.2f} $\\times$ {component.height:.2f}",
                    _latex_escape(component.material),
                    f"{conductivity:.1f}",
                ]
            )
            + r" \\"
        )
    return "\n".join(rows)


def _build_run_table_rows(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return r"\multicolumn{5}{c}{暂无 run 数据} \\"

    rows: list[str] = []
    for item in runs:
        status = item.get("validation_status", "-")
        change_desc = _short_change_list(item.get("changed_paths", []))
        effect_desc = _format_effect(item)
        note = _validation_note(item)
        if item.get("run_id") == "run_0009":
            note = r"\alert{最大转折}"
        rows.append(
            " & ".join(
                [
                    _latex_escape(item.get("run_id", "-")),
                    _latex_escape(status),
                    _latex_escape(change_desc),
                    _latex_escape(effect_desc),
                    note if note.startswith(r"\alert") else _latex_escape(note),
                ]
            )
            + r" \\"
        )
    return "\n".join(rows)


def _find_run_dir(runs_root: Path, run_id: str | None) -> Path | None:
    if not run_id:
        return None
    candidate = runs_root / run_id
    return candidate if candidate.exists() else None


def _figure_paths(runs_root: Path, runs: list[dict[str, Any]]) -> dict[str, Path | None]:
    first_run_id = runs[0]["run_id"] if runs else None
    last_run_id = runs[-1]["run_id"] if runs else None
    first_run_dir = _find_run_dir(runs_root, first_run_id)
    last_run_dir = _find_run_dir(runs_root, last_run_id)

    baseline_figure_root = ROOT / "outputs" / "02_multicomponent_steady_heat" / "figures"
    first_figure_root = first_run_dir / "outputs" / "figures" if first_run_dir else baseline_figure_root
    last_figure_root = last_run_dir / "outputs" / "figures" if last_run_dir else None
    trend_root = runs_root / "figures"

    return {
        "layout": (first_figure_root / "layout.png") if first_figure_root else None,
        "mesh": (first_figure_root / "mesh.png") if first_figure_root else None,
        "subdomains": (first_figure_root / "subdomains.png") if first_figure_root else None,
        "baseline_temperature": (first_figure_root / "temperature.png") if first_figure_root else None,
        "chip_max_trend": trend_root / "chip_max_trend.png",
        "delta_trend": trend_root / "delta_trend.png",
        "category_timeline": trend_root / "category_timeline.png",
        "final_layout": (last_figure_root / "layout.png") if last_figure_root else None,
        "final_temperature": (last_figure_root / "temperature.png") if last_figure_root else None,
    }


def _find_run_item(runs: list[dict[str, Any]], run_id: str) -> dict[str, Any] | None:
    return next((item for item in runs if item.get("run_id") == run_id), None)


def _increment_run_id(run_id: str | None, step: int = 1) -> str | None:
    if not run_id:
        return None
    parts = run_id.split("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return f"run_{int(parts[1]) + step:04d}"


def _first_valid_numeric(items: list[Any]) -> float | None:
    for item in items:
        if isinstance(item, (int, float)):
            return float(item)
    return None


def _group_roots(root: Path) -> list[Path]:
    return sorted([path for path in root.glob("group_*") if path.is_dir()])


def _select_representative_root(runs_root: Path) -> Path:
    groups = _group_roots(runs_root)
    if not groups:
        return runs_root
    preferred = runs_root / "group_06"
    if preferred.exists():
        return preferred
    return groups[0]


def _load_group_comparison_rows(runs_root: Path) -> list[dict[str, Any]]:
    comparison_path = runs_root / "consistency_10x15_group_comparison.json"
    if not comparison_path.exists():
        return []
    payload = json.loads(comparison_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return []


def _comparison_figure_paths(runs_root: Path) -> dict[str, Path]:
    figures_dir = runs_root / "figures"
    return {
        "trajectories": figures_dir / "consistency_10x15_trajectories.png",
        "final_chip_max": figures_dir / "consistency_10x15_final_chip_max.png",
        "first_base_k_round": figures_dir / "consistency_10x15_first_base_k_round.png",
    }


def _select_key_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    def add_item(candidate: dict[str, Any] | None) -> None:
        if candidate is None:
            return
        run_id = candidate.get("run_id")
        if any(item.get("run_id") == run_id for item in selected):
            return
        selected.append(candidate)

    add_item(runs[0] if runs else None)
    add_item(next((item for item in runs if item.get("validation_status") == "invalid"), None))
    add_item(
        next(
            (
                item
                for item in runs
                if "materials.base_material.conductivity" in item.get("changed_paths", [])
            ),
            None,
        )
    )
    add_item(
        min(
            (item for item in runs if isinstance(item.get("delta_chip_max"), (int, float))),
            key=lambda item: item["delta_chip_max"],
            default=None,
        )
    )
    add_item(runs[-1] if runs else None)
    return selected


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _representative_story(representative_root: Path, runs: list[dict[str, Any]]) -> dict[str, Any]:
    key_run = next(
        (
            item
            for item in runs
            if "materials.base_material.conductivity" in item.get("changed_paths", [])
        ),
        None,
    )
    if key_run is None:
        key_run = runs[0] if runs else {}

    key_run_id = key_run.get("run_id", "run_0011")
    next_run_id = _increment_run_id(key_run_id) or "run_0012"
    key_run_dir = representative_root / key_run_id
    next_run_dir = representative_root / next_run_id

    system_prompt = _read_text_if_exists(ROOT / "prompts" / "plan_changes_system.md") or ""
    system_rules = [
        "只返回 JSON，不输出 Markdown" if "Return JSON only" in system_prompt else "输出保持结构化",
        "提案必须保守且物理上合理" if "physically plausible" in system_prompt else "提案要物理合理",
        "优先少量但高影响的改动" if "high-impact changes" in system_prompt else "优先高影响杠杆",
        "不要修改与当前约束无关的字段" if "unrelated" in system_prompt else "避免无关改动",
    ]

    key_state = _load_state_if_exists(key_run_dir / "state.yaml")
    key_eval = _load_json_if_exists(key_run_dir / "evaluation.json") or {}
    next_eval = _load_json_if_exists(next_run_dir / "evaluation.json") or {}
    key_proposal = _load_json_if_exists(key_run_dir / "proposal.json") or {}
    key_validation = _load_json_if_exists(key_run_dir / "proposal_validation.json") or {}
    key_prompt = _read_text_if_exists(key_run_dir / "prompt.txt") or ""

    early_invalid = _load_json_if_exists(representative_root / "run_0005" / "proposal_validation.json") or {}
    geometry_proposal = _load_json_if_exists(representative_root / "run_0006" / "proposal.json") or {}
    recent_run_ids = []
    if key_run_id:
        previous_1 = _increment_run_id(key_run_id, -1)
        previous_2 = _increment_run_id(key_run_id, -2)
        if previous_2:
            recent_run_ids.append(previous_2)
        if previous_1:
            recent_run_ids.append(previous_1)
    recent_deltas = [
        item.get("delta_chip_max")
        for item in (_find_run_item(runs, run_id) for run_id in recent_run_ids)
        if item is not None
    ]

    first_before = _first_valid_numeric([runs[0].get("chip_max_before")]) if runs else None
    plateau_before = _first_valid_numeric([key_eval.get("objective_summary", {}).get("chip_max_temperature")])
    early_total_drop = None
    if first_before is not None and plateau_before is not None:
        early_total_drop = plateau_before - first_before

    geometry_run = _find_run_item(runs, "run_0006") or {}
    invalid_reason = ""
    invalid_reasons = early_invalid.get("reasons", [])
    if invalid_reasons:
        invalid_reason = invalid_reasons[0]
    invalid_checked_change = (early_invalid.get("checked_changes") or [{}])[0]

    key_change = (key_proposal.get("changes") or [{}])[0]
    before_value = key_change.get("old")
    after_value = key_change.get("new")
    effect_before = _first_valid_numeric(
        [
            key_eval.get("objective_summary", {}).get("chip_max_temperature"),
            key_run.get("chip_max_before"),
        ]
    )
    effect_after = _first_valid_numeric(
        [
            next_eval.get("objective_summary", {}).get("chip_max_temperature"),
            key_run.get("chip_max_after"),
        ]
    )
    effect_delta = None
    if effect_before is not None and effect_after is not None:
        effect_delta = effect_after - effect_before

    spreader_k = None
    base_k = None
    spreader_width = None
    if key_state is not None:
        spreader_k = key_state.materials["spreader_material"].conductivity
        base_k = key_state.materials["base_material"].conductivity
        spreader = next((item for item in key_state.components if item.name == "heat_spreader"), None)
        if spreader is not None:
            spreader_width = spreader.width

    history_hint = ""
    if "Optimization history summary:" in key_prompt:
        history_hint = key_prompt.split("Optimization history summary:", 1)[1].strip().splitlines()[0]

    proposal_model = key_proposal.get("model_info", {}).get("model", "-")
    prompt_facts = [
        f"当前芯片峰值 {effect_before:.3f} degC，高于约束 85.0 degC。"
        if effect_before is not None
        else "当前输入里明确给出了芯片峰值与约束违反情况。",
        (
            f"当轮状态中，spreader_k={spreader_k:.1f}，base_k={base_k:.1f}，"
            f"spreader 宽度={spreader_width:.2f} m。"
        )
        if spreader_k is not None and base_k is not None and spreader_width is not None
        else "当前状态同时包含材料参数、几何参数和边界条件。",
        (
            f"前两轮改善仅 {_fmt_delta(recent_deltas[0], 4)} 和 {_fmt_delta(recent_deltas[1], 4)} degC，"
            "已明显进入平台期。"
        )
        if len(recent_deltas) >= 2
        else "提示词中包含了最近若干轮的改善趋势与策略摘要。",
        (
            "history 明确提示：近期改善极小，几何修改已频繁触碰合法性边界。"
            if "geometry changes are hitting legality limits" in history_hint
            else "history 摘要会提醒 LLM 注意平台期与非法提案模式。"
        ),
    ]

    switch_facts = [
        (
            f"run_0001 起优先调 spreader_k，累计仅变化 {early_total_drop:+.3f} degC。"
            if early_total_drop is not None
            else "前几轮优先使用的是热点上方的局部材料杠杆 spreader_k。"
        ),
        (
            (
                f"run_0005 试图把 spreader_k 提到 {invalid_checked_change.get('new', 0):.2f}，"
                "超过上界 500，被 validator 拒绝。"
            )
            if isinstance(invalid_checked_change.get("new"), (int, float))
            else (
                f"run_0005 提案因越过上界而被拒：{_clip_text(invalid_reason, 48)}。"
                if invalid_reason
                else "run_0005 出现了材料参数越上界的非法提案。"
            )
        ),
        (
            f"run_0006 将 spreader 宽度从 {geometry_proposal.get('changes', [{}])[0].get('old', 0.7)} "
            f"调到 {geometry_proposal.get('changes', [{}])[0].get('new', 0.9)}，"
            f"结果仅 {_fmt_delta(geometry_run.get('delta_chip_max'), 5)} degC。"
            if geometry_proposal.get("changes")
            else "随后尝试过几何放宽，但改善几乎可以忽略。"
        ),
        "因此需要从“热点上方扩散”切换到“整条散热路径”的全局瓶颈，也就是 base_k。",
    ]

    proposal_change_path = key_change.get("path", "materials.base_material.conductivity")
    proposal_action_lines = [
        f"模型：{proposal_model}",
        f"路径：{proposal_change_path}",
        (
            f"动作：set，{before_value:.1f} -> {after_value:.1f}"
            if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float))
            else "动作：set"
        ),
        (
            "理由：提升底板导热率，增强热扩展块到两侧冷端的整体传热通道。"
            if proposal_change_path == "materials.base_material.conductivity"
            else "理由：通过单步高影响改动优先降低芯片峰值。"
        ),
    ]

    validator_lines = [
        "validator 结果：valid=true，允许进入执行阶段。"
        if key_validation.get("valid") is True
        else "validator 结果：未通过，执行阶段不会写入 next_state。",
        "执行器会把提案写入 next_state.yaml，并重新运行 FEniCSx 求解、评估与画图。",
        "因此每轮都有可回滚快照：state / evaluation / proposal / validation / outputs。",
    ]

    effect_lines = [
        (
            f"{key_run_id} 求解后芯片峰值为 {effect_before:.3f} degC，仍处于不可行状态。"
            if effect_before is not None
            else f"{key_run_id} 仍未满足温度约束。"
        ),
        (
            f"{next_run_id} 兑现后降到 {effect_after:.3f} degC，单步变化 {_fmt_delta(effect_delta, 3)} degC。"
            if effect_after is not None and effect_delta is not None
            else "下一轮 evaluation 会显示该 proposal 的真实物理效果。"
        ),
        (
            "这一跳不是局部小修，而是把热从热扩展块更快送到底板，再送往左右 25 degC 冷端。"
        ),
        (
            "系统因此从违反约束切换到可行域，说明 base_k 是该案例里的全局决定性杠杆。"
            if next_eval.get("feasible") is True
            else "这一步显著改善了目标值，并帮助系统靠近或进入可行域。"
        ),
    ]

    return {
        "system_rules": system_rules,
        "prompt_facts": prompt_facts,
        "switch_facts": switch_facts,
        "proposal_action_lines": proposal_action_lines,
        "validator_lines": validator_lines,
        "effect_lines": effect_lines,
    }


def build_demo_beamer(*, runs_root: str | Path, output_path: str | Path) -> dict[str, str]:
    runs_root = Path(runs_root)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    representative_root = _select_representative_root(runs_root)
    aggregate_root = runs_root
    summary = _load_or_build_summary(representative_root)
    runs = summary.get("runs", [])
    figures = _figure_paths(representative_root, runs)
    aggregate_figures = _comparison_figure_paths(aggregate_root)
    comparison_rows = _load_group_comparison_rows(aggregate_root)

    baseline_state = _load_state_if_exists(representative_root / "run_0001" / "state.yaml")
    if baseline_state is None:
        baseline_state = _load_state_if_exists(ROOT / "states" / "baseline_multicomponent.yaml")
    final_state = _load_state_if_exists(representative_root / "run_0015" / "state.yaml")
    if final_state is None and runs:
        final_state = _load_state_if_exists(representative_root / runs[-1]["run_id"] / "state.yaml")

    baseline_chip_max = _first_valid_numeric([item.get("chip_max_before") for item in runs[:1]])
    final_chip_max = _first_valid_numeric(
        [item.get("chip_max_before") for item in reversed(runs)]
    )
    constraint_limit = _first_valid_numeric([item.get("constraint_limit") for item in runs])

    baseline_component_rows = _build_component_rows(baseline_state)
    material_rows = _build_variable_rows({"material", "load"})
    geometry_rows = _build_variable_rows({"geometry"})
    key_run_rows = _build_run_table_rows(_select_key_runs(runs))
    representative_story = _representative_story(representative_root, runs)

    final_state_summary = "未生成最终状态"
    if final_state is not None:
        spreader = next((item for item in final_state.components if item.name == "heat_spreader"), None)
        if spreader is not None:
            final_state_summary = (
                f"热扩展块宽度 {spreader.width:.2f} m，"
                f"底板导热率 {final_state.materials['base_material'].conductivity:.1f}，"
                f"热扩展块导热率 {final_state.materials['spreader_material'].conductivity:.1f}"
            )

    group_count = len(comparison_rows) or len(_group_roots(aggregate_root)) or 1
    feasible_count = sum(
        1 for item in comparison_rows if isinstance(item.get("final_chip_max"), (int, float)) and item["final_chip_max"] <= 85.0
    )
    final_values = [
        float(item["final_chip_max"])
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float))
    ]
    mean_final_chip_max = _average(final_values)
    best_final = min(final_values) if final_values else None
    worst_final = max(final_values) if final_values else None
    best_groups = [
        item["group"]
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float)) and item["final_chip_max"] == best_final
    ]
    best_groups_text = "、".join(best_groups) if best_groups else "暂无"
    best_tier_text = "、".join(
        item["group"]
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float)) and item["final_chip_max"] < 50.0
    ) or "暂无"
    mid_tier_text = "、".join(
        item["group"]
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float)) and 50.0 <= item["final_chip_max"] < 65.0
    ) or "暂无"
    partial_tier_text = "、".join(
        item["group"]
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float)) and 65.0 <= item["final_chip_max"] <= 85.0
    ) or "暂无"
    failed_tier_text = "、".join(
        item["group"]
        for item in comparison_rows
        if isinstance(item.get("final_chip_max"), (int, float)) and item["final_chip_max"] > 85.0
    ) or "暂无"
    representative_label = representative_root.name if representative_root != runs_root else "当前 runs_root"

    tex = rf"""\documentclass[aspectratio=169]{{ctexbeamer}}
\usetheme{{Madrid}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{tabularx}}
\usepackage{{array}}
\usepackage{{amsmath}}
\usepackage{{hyperref}}
\setbeamertemplate{{navigation symbols}}{{}}
\setbeamersize{{text margin left=0.6cm,text margin right=0.6cm}}
\newcommand{{\missingfigure}}[2]{{\fbox{{\parbox[c][#2][c]{{#1}}{{\centering 图像未生成}}}}}}

\title{{大模型驱动二维稳态导热优化闭环}}
\author{{ZhaochengLi}}
\institute{{中科院微小卫星创新院}}
\date{{\today}}

\begin{{document}}

\begin{{frame}}
\titlepage
\end{{frame}}

\begin{{frame}}{{汇报结构}}
\tableofcontents
\end{{frame}}

\section{{问题定义}}

\begin{{frame}}{{问题定义与目标}}
\begin{{itemize}}
\item 当前案例研究一个二维稳态导热问题，求解对象是标量温度场 $T(x,y)$。
\item 几何上包含 3 个矩形组件：底板、芯片、热扩展块。
\item baseline 的芯片最高温度约为 { _fmt_float(baseline_chip_max) } degC，约束为 $T_{{\max,\mathrm{{chip}}}} \le { _fmt_float(constraint_limit, 1) }$ degC。
\item 因此我们需要的不只是“算一次温度场”，还需要一个能持续修改设计参数、验证合法性并比较结果的闭环。
\end{{itemize}}
\vspace{{0.3cm}}
\begin{{block}}{{当前模型的变量分工}}
PDE 的场变量只有温度 $T$；LLM 迭代修改的是材料参数、几何参数和热源参数，而不是直接改求解代码。
\end{{block}}
\end{{frame}}

\begin{{frame}}{{物理模型与数学形式}}
\small
\textbf{{控制方程}}
\[
-\nabla \cdot \left(k \nabla T \right) = q \qquad \text{{in }} \Omega
\]
\textbf{{边界条件}}
\[
T = 25^\circ \mathrm{{C}} \quad \text{{on }} \Gamma_{{left}} \cup \Gamma_{{right}}
\]
\[
-k \nabla T \cdot n = 0 \quad \text{{on the remaining boundary}}
\]
\textbf{{变分形式}}
\[
\text{{Find }} T \in V \text{{ with prescribed Dirichlet data, such that}}
\]
\[
\int_{{\Omega}} k \nabla T \cdot \nabla v \, \mathrm{{d}}x
=
\int_{{\Omega}} q v \, \mathrm{{d}}x,
\quad \forall v \in V_0
\]
\begin{{itemize}}
\item $k$ 为各子区域导热率，$q$ 为芯片区域等效体热源。
\item 这是一个单场线性稳态热传导问题，适合作为 FEniCSx 入门与 LLM 闭环优化模板。
\end{{itemize}}
\end{{frame}}

\section{{组件建模}}

\begin{{frame}}{{组件建模与 baseline 参数}}
\scriptsize
\begin{{tabularx}}{{\linewidth}}{{l l l l l}}
\toprule
组件 & 左下角 $(x_0,y_0)$ & 尺寸 $(w,h)$ & 材料 & $k$ \\
\midrule
{baseline_component_rows}
\bottomrule
\end{{tabularx}}
\vspace{{0.2cm}}
\begin{{itemize}}
\item 设计域：$(0,0)$ 到 $(1.2,0.5)$。
\item 芯片上施加等效体热源 $15000\,\mathrm{{W/m^3}}$。
\item 采用 SI 风格单位：长度 m，温度 degC，导热率 $\mathrm{{W/(m\cdot K)}}$。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{组件最初摆放}}
\centering
{_include_graphic(figures["layout"], width="0.82\\linewidth", height="0.55\\textheight")}
\vspace{{0.2cm}}
\begin{{itemize}}
\item 底板位于最下层，连接两侧 25 degC 冷端边界。
\item 芯片位于中部，是唯一发热组件。
\item 热扩展块位于芯片上方，承担横向扩散任务。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{网格、子区域与离散方式}}
\begin{{columns}}[T]
\column{{0.48\linewidth}}
\centering
{_include_graphic(figures["mesh"], width="0.95\\linewidth")}
\\[0.15cm]
\footnotesize 网格图
\column{{0.48\linewidth}}
\centering
{_include_graphic(figures["subdomains"], width="0.95\\linewidth")}
\\[0.15cm]
\footnotesize 子区域标签图
\end{{columns}}
\vspace{{0.2cm}}
\begin{{itemize}}
\item 温度场函数空间：$V_h = P_1$ Lagrange。
\item 材料场与热源场：DG0 分片常数。
\item 线性求解器：LU。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{baseline 仿真结果}}
\begin{{columns}}[T]
\column{{0.57\linewidth}}
\centering
{_include_graphic(figures["baseline_temperature"], width="0.98\\linewidth")}
\column{{0.40\linewidth}}
\small
\begin{{block}}{{关键指标}}
\begin{{itemize}}
\item 芯片最高温：{ _fmt_float(baseline_chip_max) } degC
\item 约束上限：{ _fmt_float(constraint_limit, 1) } degC
\item 判定：\alert{{不满足约束}}
\end{{itemize}}
\end{{block}}
\begin{{block}}{{物理解读}}
\begin{{itemize}}
\item 热点集中在芯片及热扩展块附近。
\item 温度沿底板向左右冷端传递。
\item baseline 已具备明确优化空间。
\end{{itemize}}
\end{{block}}
\end{{columns}}
\end{{frame}}

\section{{LLM 优化闭环}}

\begin{{frame}}{{为什么需要 LLM 参与优化}}
\begin{{itemize}}
\item 单次仿真只能回答“当前设计的温度场是什么”。
\item 工程问题真正关心的是：如果不满足约束，下一步应该改哪里、改多少、是否合法。
\item 当前系统不是让 LLM 直接改 Python，而是让它对结构化 state 提出修改建议。
\item 因此整个 workflow 变成：\textbf{{状态驱动建模}} + \textbf{{FEniCSx 求解}} + \textbf{{约束评估}} + \textbf{{LLM 提案}} + \textbf{{合法性校验}}。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{整体 workflow}}
\small
\begin{{enumerate}}
\item 读取当前 \texttt{{state.yaml}}
\item 编译几何、网格、材料场、热源场和 PDE
\item 运行 FEniCSx 求解，输出温度场和图片
\item evaluator 提取指标并判断是否违反约束
\item DashScope \texttt{{qwen3.5-plus}} 生成结构化 proposal
\item validator 检查变量边界、步长、重叠和越界
\item 合法则生成 \texttt{{next\_state.yaml}} 并进入下一轮
\end{{enumerate}}
\vspace{{0.2cm}}
\begin{{block}}{{关键原则}}
LLM 是受约束的提案者，不是无边界的代码修改者。
\end{{block}}
\end{{frame}}

\begin{{frame}}{{run 与 iteration 的区别}}
\small
\begin{{itemize}}
\item \texttt{{run\_0001}} 是目录编号，每个目录保存一次 iteration 的完整快照。
\item 真正的“第几轮”看 \texttt{{decision.json}} 里的 \texttt{{iteration}}。
\item 一个 run 目录中通常包含：
\end{{itemize}}
\begin{{center}}
\begin{{tabular}}{{llll}}
\texttt{{state.yaml}} & \texttt{{evaluation.json}} & \texttt{{proposal.json}} & \texttt{{decision.json}} \\
\texttt{{proposal\_validation.json}} & \texttt{{next\_state.yaml}} & \texttt{{outputs/}} & \\
\end{{tabular}}
\end{{center}}
\begin{{itemize}}
\item 本轮 proposal 的效果往往要到下一轮 evaluation 才能看到。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{LLM 可修改参数：材料与载荷}}
\scriptsize
\begin{{tabularx}}{{\linewidth}}{{l X l l l}}
\toprule
变量标签 & 路径 & 类别 & 范围 & 推荐方向 \\
\midrule
{material_rows}
\bottomrule
\end{{tabularx}}
\vspace{{0.2cm}}
\begin{{itemize}}
\item 当前真实模型：DashScope \texttt{{qwen3.5-plus}}。
\item 热源变量只用于 what-if 场景探索，不是当前主设计杠杆。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{LLM 可修改参数：几何与合法性约束}}
\scriptsize
\begin{{tabularx}}{{\linewidth}}{{l X l l l}}
\toprule
变量标签 & 路径 & 类别 & 范围 & 推荐方向 \\
\midrule
{geometry_rows}
\bottomrule
\end{{tabularx}}
\vspace{{0.15cm}}
\begin{{block}}{{proposal validation}}
\begin{{itemize}}
\item 导热率必须在变量上下界内，单步变化不能超过 $2.0\times$
\item 尺寸单步变化不能超过 $1.5\times$
\item 位置移动不能超过设计域宽高的 $25\%$
\item 组件不能重叠，也不能超出允许设计域
\end{{itemize}}
\end{{block}}
\end{{frame}}

\section{{代表性单跑}}

\begin{{frame}}{{代表性单跑：15轮温度轨迹}}
\centering
{_include_graphic(figures["chip_max_trend"], width="0.85\\linewidth", height="0.52\\textheight")}
\vspace{{0.1cm}}
\begin{{itemize}}
\item 本页默认选用代表性单跑：\texttt{{{_latex_escape(representative_label)}}}。
\item 这类单跑通常会经历“前期平台 + 中后期策略切换”的形态，而不是每轮都明显下降。
\item 单跑章节的作用是解释闭环如何工作；跨组稳定性要看后面的 10 组正式实验。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：关键轮次与策略切换}}
\scriptsize
\begin{{tabularx}}{{\linewidth}}{{p{{1.25cm}} p{{1.15cm}} X X p{{2.1cm}}}}
\toprule
轮次 & 状态 & 修改内容 & 芯片峰值变化 (degC) & 说明 \\
\midrule
{key_run_rows}
\bottomrule
\end{{tabularx}}
\vspace{{0.15cm}}
\begin{{itemize}}
\item 代表性路径里，前期通常先调 \texttt{{spreader\_k}}，改善有限。
\item 真正的大幅降温往往出现在识别并切换到底板导热率 \texttt{{base\_k}} 之后。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：LLM 在关键轮次看到了什么}}
\small
\begin{{columns}}[T]
\column{{0.46\linewidth}}
\begin{{block}}{{系统 prompt 的硬约束}}
\begin{{itemize}}
\item {_latex_escape(representative_story["system_rules"][0])}
\item {_latex_escape(representative_story["system_rules"][1])}
\item {_latex_escape(representative_story["system_rules"][2])}
\item {_latex_escape(representative_story["system_rules"][3])}
\end{{itemize}}
\end{{block}}
\column{{0.51\linewidth}}
\begin{{block}}{{run\_0011 输入摘要}}
\begin{{itemize}}
\item {_latex_escape(representative_story["prompt_facts"][0])}
\item {_latex_escape(representative_story["prompt_facts"][1])}
\item {_latex_escape(representative_story["prompt_facts"][2])}
\item {_latex_escape(representative_story["prompt_facts"][3])}
\end{{itemize}}
\end{{block}}
\end{{columns}}
\vspace{{0.1cm}}
\begin{{itemize}}
\item LLM 看到的不是一句“帮我降温”，而是完整的当前 state、可编辑变量表、evaluation 指标和历史轨迹摘要。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：为什么会切换到 base\_k}}
\small
\begin{{block}}{{前期策略为什么失效}}
\begin{{itemize}}
\item {_latex_escape(representative_story["switch_facts"][0])}
\item {_latex_escape(representative_story["switch_facts"][1])}
\item {_latex_escape(representative_story["switch_facts"][2])}
\end{{itemize}}
\end{{block}}
\begin{{block}}{{策略切换的物理含义}}
\begin{{itemize}}
\item {_latex_escape(representative_story["switch_facts"][3])}
\item 也就是说，局部扩散已经不是主要瓶颈，真正的限制来自热量能否继续穿过底板并传到左右冷端。
\end{{itemize}}
\end{{block}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：关键 proposal 与执行动作}}
\small
\begin{{columns}}[T]
\column{{0.52\linewidth}}
\begin{{block}}{{proposal.json 摘要}}
\begin{{itemize}}
\item {_latex_escape(representative_story["proposal_action_lines"][0])}
\item \texttt{{{_latex_escape(representative_story["proposal_action_lines"][1].replace("路径：", ""))}}}
\item {_latex_escape(representative_story["proposal_action_lines"][2])}
\item {_latex_escape(representative_story["proposal_action_lines"][3])}
\end{{itemize}}
\end{{block}}
\column{{0.43\linewidth}}
\begin{{block}}{{validator + executor}}
\begin{{itemize}}
\item {_latex_escape(representative_story["validator_lines"][0])}
\item {_latex_escape(representative_story["validator_lines"][1])}
\item {_latex_escape(representative_story["validator_lines"][2])}
\end{{itemize}}
\end{{block}}
\end{{columns}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：关键动作兑现后的效果}}
\small
\begin{{columns}}[T]
\column{{0.50\linewidth}}
\begin{{block}}{{run\_0011 -> run\_0012}}
\begin{{itemize}}
\item {_latex_escape(representative_story["effect_lines"][0])}
\item {_latex_escape(representative_story["effect_lines"][1])}
\end{{itemize}}
\end{{block}}
\begin{{block}}{{为什么这一跳这么大}}
\begin{{itemize}}
\item {_latex_escape(representative_story["effect_lines"][2])}
\item {_latex_escape(representative_story["effect_lines"][3])}
\end{{itemize}}
\end{{block}}
\column{{0.46\linewidth}}
\centering
{_include_graphic(figures["chip_max_trend"], width="0.98\\linewidth", height="0.54\\textheight")}
\\[0.08cm]
\footnotesize 曲线中的台阶式下降，对应的就是这次 \texttt{{base\_k}} 策略切换
\end{{columns}}
\end{{frame}}

\begin{{frame}}{{代表性单跑：初始与最终布局/温度场对比}}
\begin{{columns}}[T]
\column{{0.49\linewidth}}
\centering
{_include_graphic(figures["layout"], width="0.92\\linewidth", height="0.22\\textheight")}
\\[0.05cm]
{_include_graphic(figures["baseline_temperature"], width="0.92\\linewidth", height="0.22\\textheight")}
\\[0.1cm]
\footnotesize 左：baseline 布局与温度场
\column{{0.49\linewidth}}
\centering
{_include_graphic(figures["final_layout"], width="0.92\\linewidth", height="0.22\\textheight")}
\\[0.05cm]
{_include_graphic(figures["final_temperature"], width="0.92\\linewidth", height="0.22\\textheight")}
\\[0.1cm]
\footnotesize 右：最终状态布局与温度场
\end{{columns}}
\vspace{{0.15cm}}
\begin{{itemize}}
\item 最终状态摘要：{ _latex_escape(final_state_summary) }。
\item 这说明：真正决定性的是整体热路径变通畅，而不只是热点上方局部材料变好。
\end{{itemize}}
\end{{frame}}

\section{{10组 15轮正式实验}}

\begin{{frame}}{{10组 15轮正式实验：实验设置}}
\small
\begin{{itemize}}
\item 同一案例、同一 baseline、同一约束、同一真实模型：DashScope \texttt{{qwen3.5-plus}}。
\item 每组独立运行 15 轮，并允许保留非法 proposal 记录，完整观察策略切换过程。
\item 这一步的目标不是再展示“单次能不能成功”，而是回答：重复运行后，结果和策略到底有多一致。
\end{{itemize}}
\vspace{{0.2cm}}
\begin{{block}}{{本轮正式结论摘要}}
\begin{{itemize}}
\item 组数：{group_count}
\item 最终进入可行域：{feasible_count if comparison_rows else "-"} / {group_count}
\item 最终芯片峰值均值：{_fmt_float(mean_final_chip_max)}
\item 最优组：{_latex_escape(best_groups_text)}，最佳最终温度 { _fmt_float(best_final) } degC
\item 最差最终温度：{ _fmt_float(worst_final) } degC
\end{{itemize}}
\end{{block}}
\end{{frame}}

\begin{{frame}}{{10组 15轮正式实验：全组轨迹}}
\centering
{_include_graphic(aggregate_figures["trajectories"], width="0.78\\linewidth", height="0.50\\textheight")}
\vspace{{0.05cm}}
\begin{{itemize}}
\item 大多数组前半段都停在约 89.2--89.3 degC 的平台上。
\item 温度曲线是否出现台阶式下降，取决于何时切换到真正的全局杠杆。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{10组 15轮正式实验：最终结果分布}}
\centering
{_include_graphic(aggregate_figures["final_chip_max"], width="0.82\\linewidth", height="0.50\\textheight")}
\vspace{{0.15cm}}
\begin{{itemize}}
\item 最终结果不是单点收敛，而是明显分成多档。
\item 这一点说明系统具备较强的局部一致性，但还没有达到强全局收敛一致性。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{10组 15轮正式实验：第一次使用 base\_k 的轮次}}
\centering
{_include_graphic(aggregate_figures["first_base_k_round"], width="0.78\\linewidth", height="0.46\\textheight")}
\vspace{{0.05cm}}
\begin{{itemize}}
\item 这张图回答“结果差异为什么会出现”。
\item 多数组的成败差异，不在前 5 轮，而在何时把注意力从热扩展块切换到底板导热路径。
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{结果分群与机制解释}}
\small
\begin{{block}}{{结果分群}}
\begin{{itemize}}
\item 最优组（约 43 degC）：{_latex_escape(best_tier_text)}
\item 主流成功组（约 58--59 degC）：{_latex_escape(mid_tier_text)}
\item 部分成功组（约 69 degC）：{_latex_escape(partial_tier_text)}
\item 失败组（约 89 degC）：{_latex_escape(failed_tier_text)}
\end{{itemize}}
\end{{block}}
\begin{{block}}{{机制解释}}
\begin{{itemize}}
\item 前半段高频出现的是 \texttt{{spreader\_k}}，这是局部直觉杠杆。
\item 真正决定性的是 \texttt{{base\_k}}：是否及时识别、幅度是否足够、是否来得及在 15 轮窗口内兑现。
\end{{itemize}}
\end{{block}}
\end{{frame}}

\section{{结论}}

\begin{{frame}}{{结论与下一步}}
\begin{{itemize}}
\item 当前案例已经形成了一个完整的最小闭环：state 驱动建模、FEniCSx 求解、LLM 提案、proposal validation、逐轮记录、可视化与回滚。
\item 10 组正式实验表明：LLM 在这个案例上已经表现出较强的前期策略一致性，但最终效果并不唯一。
\item 最终 9/10 组进入可行域，说明系统并不脆弱；但结果分群明显，说明关键策略触发时机仍然不稳定。
\item 当前最有解释力的机制是：是否及时识别 \texttt{{base\_k}} 这个全局瓶颈，以及是否在有限轮数内把它推到足够强。
\item 当前局限：仍是二维、稳态、单温度场模型，尚未包含对流、界面热阻和瞬态过程。
\item 下一步如果继续增强，可以把跨轮记忆、策略引导和更强物理约束进一步接入闭环，让多次重复实验的结果分布更集中。
\end{{itemize}}
\end{{frame}}

\end{{document}}
"""
    output_path.write_text(tex, encoding="utf-8")
    return {"tex_path": str(output_path)}
