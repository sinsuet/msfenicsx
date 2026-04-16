# S1 Typical Layout Realism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `s1_typical` generation from sparse rectangle-only scatter to a more compact, semantically structured, mixed-shape layout pipeline while preserving the active fifteen-component, `x/y`-only paper-facing benchmark contract.

**Architecture:** Enrich the scenario template with layout semantics and mixed footprint families, add generator-side layout-quality metrics, replace uniform legal scatter with a staged semantic placement plus compactness refinement flow, make representative exports/rendering shape-aware, then update optimizer repair so mixed-shape benchmark cases remain valid throughout the official raw / union / llm path.

**Tech Stack:** Python 3.12, pytest, NumPy, PyYAML, Shapely, FEniCSx bundle exports, repository-local YAML/JSON artifacts

---

Spec reference:

- `docs/superpowers/specs/2026-04-02-s1-typical-layout-realism-design.md`

Primary guardrails:

- Keep `s1_typical` as the only active paper-facing mainline.
- Keep all fifteen components optimization-active in `x/y`; do not add any rotation design variable.
- Do not move business logic into `scenarios/`.
- Preserve generator robustness with a fallback path instead of making semantic placement all-or-nothing.
- Treat real component footprints as the geometry truth source in generator, visualization, and optimizer repair.

## File Structure

### Template And Schema Surface

- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/schema/validation.py`
- Modify: `tests/schema/test_s1_typical_template.py`

### Generator Semantics And Metrics

- Create: `core/generator/layout_metrics.py`
- Modify: `core/generator/parameter_sampler.py`
- Modify: `core/generator/layout_engine.py`
- Modify: `core/geometry/layout_rules.py`
- Modify: `tests/generator/test_layout_engine.py`
- Create: `tests/generator/test_layout_metrics.py`

### Shape-Aware Export And Rendering

- Modify: `core/solver/field_export.py`
- Modify: `visualization/static_assets.py`
- Modify: `visualization/case_pages.py`
- Modify: `tests/visualization/test_case_pages.py`
- Modify: `tests/optimizers/experiment_fixtures.py`

### Optimizer Compatibility

- Modify: `optimizers/repair.py`
- Modify: `tests/optimizers/test_repair.py`
- Modify: `tests/cli/test_cli_end_to_end.py`

### Documentation

- Modify: `README.md`

## Task 1: Add Mixed-Shape Template Semantics

**Files:**
- Modify: `scenarios/templates/s1_typical.yaml`
- Modify: `core/schema/validation.py`
- Modify: `tests/schema/test_s1_typical_template.py`

- [ ] **Step 1: Write the failing schema/template tests**

Add coverage that requires the active template to declare mixed footprint classes and layout semantics.

```python
def test_s1_typical_template_declares_mixed_shape_component_families() -> None:
    payload = yaml.safe_load(Path("scenarios/templates/s1_typical.yaml").read_text(encoding="utf-8"))

    shapes = {family["shape"] for family in payload["component_families"]}
    assert "rect" in shapes
    assert "slot" in shapes or "capsule" in shapes
    assert "circle" in shapes or "polygon" in shapes


def test_s1_typical_template_declares_layout_semantics() -> None:
    payload = yaml.safe_load(Path("scenarios/templates/s1_typical.yaml").read_text(encoding="utf-8"))

    for family in payload["component_families"]:
        assert "layout_tags" in family
        assert "placement_hint" in family
```

- [ ] **Step 2: Run the focused schema test**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/schema/test_s1_typical_template.py -v
```

Expected:

- FAIL because the current template is rectangle-only and does not define layout semantics.

- [ ] **Step 3: Update the template and validation rules**

Implement the minimal schema support needed for optional family-level layout semantics.

```python
def _validate_component_family(family: Any) -> None:
    _require_mapping(family, "component_family")
    shape = family.get("shape")
    if shape is not None and shape not in SUPPORTED_COMPONENT_SHAPES:
        raise SchemaValidationError(f"Unsupported shape '{shape}' in component family.")

    layout_tags = family.get("layout_tags", [])
    if not isinstance(layout_tags, Sequence) or isinstance(layout_tags, (str, bytes)):
        raise SchemaValidationError("component_family.layout_tags must be a sequence when provided.")

    placement_hint = family.get("placement_hint")
    if placement_hint is not None and not isinstance(placement_hint, str):
        raise SchemaValidationError("component_family.placement_hint must be a string when provided.")
```

Update the template so it includes:

- a realistic `rect / slot-or-capsule / circle-or-polygon` mix
- a higher total area budget
- `layout_tags`
- `placement_hint`
- optional `adjacency_group`
- optional preferred `clearance`
- family-level fixed-or-choice orientation policies where needed

- [ ] **Step 4: Re-run the focused schema test**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  scenarios/templates/s1_typical.yaml \
  core/schema/validation.py \
  tests/schema/test_s1_typical_template.py
git commit -m "feat: enrich s1_typical layout template semantics"
```

## Task 2: Add Layout-Quality Metrics And Regression Gates

**Files:**
- Create: `core/generator/layout_metrics.py`
- Modify: `tests/generator/test_layout_engine.py`
- Create: `tests/generator/test_layout_metrics.py`

- [ ] **Step 1: Write failing layout-quality tests**

Add generator-quality tests that describe the desired compactness behavior without pinning exact coordinates.

```python
def test_measure_layout_quality_reports_compactness_fields() -> None:
    case = generate_case("scenarios/templates/s1_typical.yaml", seed=11).to_dict()

    metrics = measure_layout_quality(case, placement_region={"x_min": 0.05, "x_max": 0.95, "y_min": 0.05, "y_max": 0.72})

    assert metrics.component_area_ratio > 0.30
    assert metrics.bbox_fill_ratio > 0.30
    assert metrics.component_count == 15


def test_layout_quality_is_stable_across_seed_sample() -> None:
    main_deck = {"x_min": 0.05, "x_max": 0.95, "y_min": 0.05, "y_max": 0.72}
    fill_ratios = []
    for seed in range(1, 11):
        case = generate_case("scenarios/templates/s1_typical.yaml", seed=seed).to_dict()
        fill_ratios.append(measure_layout_quality(case, placement_region=main_deck).bbox_fill_ratio)

    assert median(fill_ratios) > 0.30
```

- [ ] **Step 2: Run the red generator tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py -v
```

Expected:

- FAIL because no layout metric helper exists yet and current scatter layouts do not meet the new thresholds.

- [ ] **Step 3: Implement the layout metric helper**

Create a focused metrics module that computes reusable quality signals from generated cases.

```python
@dataclass(slots=True, frozen=True)
class LayoutQualityMetrics:
    component_count: int
    component_area_ratio: float
    bbox_fill_ratio: float
    nearest_neighbor_gap_mean: float
    centroid_dispersion: float


def measure_layout_quality(case_payload: dict[str, Any], placement_region: dict[str, float]) -> LayoutQualityMetrics:
    polygons = [component_polygon(component) for component in case_payload["components"]]
    total_area = sum(float(polygon.area) for polygon in polygons)
    # compute placement-region area, bounding-envelope area, nearest-neighbor gaps, centroid spread
    return LayoutQualityMetrics(...)
```

- [ ] **Step 4: Re-run the generator tests**

Run the same pytest command.

Expected:

- PASS once the helper exists and the template/generator combination meets the new thresholds.

- [ ] **Step 5: Commit**

```bash
git add \
  core/generator/layout_metrics.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py
git commit -m "test: add layout quality regression metrics"
```

## Task 3: Replace Uniform Scatter With Semantic Placement And Compactness Refinement

**Files:**
- Modify: `core/generator/parameter_sampler.py`
- Modify: `core/generator/layout_engine.py`
- Modify: `core/geometry/layout_rules.py`
- Modify: `tests/generator/test_layout_engine.py`

- [ ] **Step 1: Add failing behavior tests for semantic placement**

Describe the new generator expectations in terms of ordering and broad placement behavior rather than exact coordinates.

```python
def test_place_components_keeps_anchor_families_in_preferred_bands() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)
    by_family = {component["family_id"]: component for component in placed}

    assert by_family["c12"]["pose"]["y"] >= 0.58


def test_place_components_improves_bbox_fill_ratio_over_simple_scatter() -> None:
    template = load_template_model("scenarios/templates/s1_typical.yaml")
    sampled = sample_template_parameters(template, seed=11)

    placed = place_components(template=template, sampled_components=sampled["components"], seed=11)
    quality = measure_layout_quality(
        {"components": placed},
        placement_region=template.placement_regions[0],
    )

    assert quality.bbox_fill_ratio > 0.30
```

- [ ] **Step 2: Run the red generator behavior tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py -v
```

Expected:

- FAIL because the current engine still samples uniformly and ignores semantic hints.

- [ ] **Step 3: Implement staged placement and local refinement**

Refactor the layout engine into clear phases with a safe fallback.

```python
def place_components(template: ScenarioTemplate, sampled_components: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    try:
        buckets = _build_semantic_buckets(sampled_components)
        placed = _place_semantic_buckets(template, buckets, rng)
        return _refine_layout_compactness(template, placed, rng)
    except LayoutGenerationError:
        return _place_components_with_uniform_fallback(template, sampled_components, rng)
```

Add helpers for:

- semantic bucket ordering
- anchor-band candidate generation
- preferred-clearance checks
- adjacency-group clustering
- compactness score comparison
- legal local move refinement

Keep all legality decisions grounded in existing polygon overlap and keep-out checks.

- [ ] **Step 4: Re-run the focused generator tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/generator/parameter_sampler.py \
  core/generator/layout_engine.py \
  core/geometry/layout_rules.py \
  tests/generator/test_layout_engine.py
git commit -m "feat: add semantic layout generation for s1_typical"
```

## Task 4: Preserve Real Footprints In Field Exports And Page Rendering

**Files:**
- Modify: `core/solver/field_export.py`
- Modify: `visualization/static_assets.py`
- Modify: `visualization/case_pages.py`
- Modify: `tests/visualization/test_case_pages.py`
- Modify: `tests/optimizers/experiment_fixtures.py`

- [ ] **Step 1: Add failing rendering tests**

Extend the visualization tests so they require outline-aware rendering when footprint data is present.

```python
def test_render_case_page_writes_shape_aware_layout_svg(tmp_path: Path) -> None:
    mode_root = create_mode_root_with_seed_bundles(tmp_path, mode="raw", seeds=(11,))
    representative_root = mode_root / "seeds" / "seed-11" / "representatives" / "knee"

    output_path = render_case_page(representative_root)
    layout_svg = (representative_root / "figures" / "layout.svg").read_text(encoding="utf-8")

    assert "<polygon" in layout_svg or "<path" in layout_svg
```

- [ ] **Step 2: Run the red visualization tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest tests/visualization/test_case_pages.py -v
```

Expected:

- FAIL because exports currently preserve only rectangular bounds and rendering uses `svg_rect` for every component.

- [ ] **Step 3: Implement shape-aware serialization and rendering**

Preserve component outlines in field export and teach the renderer to draw them.

```python
def _serialize_component(component: dict[str, Any]) -> dict[str, Any]:
    polygon = component["polygon"]
    outline = [(float(x), float(y)) for x, y in polygon.exterior.coords[:-1]]
    return {
        "component_id": str(component["component_id"]),
        "outline": outline,
        "bounds": {...},
    }
```

```python
def _render_layout_overlay(...):
    if component.get("outline"):
        parts.append(svg_polygon(projected_points, ...))
    else:
        parts.append(svg_rect(...))
```

Add the minimum helper surface needed in `visualization/static_assets.py`, and update fixtures to include outline data where tests rely on exported layout payloads.

- [ ] **Step 4: Re-run the visualization tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  core/solver/field_export.py \
  visualization/static_assets.py \
  visualization/case_pages.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/experiment_fixtures.py
git commit -m "feat: render s1_typical layouts with real footprints"
```

## Task 5: Make Optimizer Repair Shape-Aware

**Files:**
- Modify: `optimizers/repair.py`
- Modify: `tests/optimizers/test_repair.py`
- Modify: `tests/cli/test_cli_end_to_end.py`

- [ ] **Step 1: Add failing repair and CLI regression tests**

Cover the mixed-shape benchmark path explicitly.

```python
def test_repair_case_from_vector_restores_mixed_shape_geometry() -> None:
    case = _case()
    spec = _spec()
    vector = extract_decision_vector(case, spec)

    for component_index in range(4):
        vector[component_index * 2] = 0.18
        vector[component_index * 2 + 1] = 0.18

    repaired = repair_case_from_vector(case, spec, np.asarray(vector, dtype=np.float64), radiator_span_max=RADIATOR_SPAN_MAX)

    assert_case_geometry_contracts(repaired)
```

```python
def test_generate_case_then_solve_cli_smoke_preserves_mixed_shapes(tmp_path: Path) -> None:
    ...
    payload = yaml.safe_load(case_files[0].read_text(encoding="utf-8"))
    assert len({component["shape"] for component in payload["components"]}) > 1
```

- [ ] **Step 2: Run the red optimizer and CLI tests**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/optimizers/test_repair.py \
  tests/cli/test_cli_end_to_end.py -v
```

Expected:

- FAIL because `optimizers/repair.py` still assumes `geometry.width` and `geometry.height`.

- [ ] **Step 3: Refactor repair to use footprint-aware separation**

Replace rectangle-only overlap deltas with geometry derived from actual polygons or their current footprint extents.

```python
def _component_overlap_deltas(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, float]:
    left_polygon = component_polygon(left)
    right_polygon = component_polygon(right)
    left_min_x, left_min_y, left_max_x, left_max_y = left_polygon.bounds
    right_min_x, right_min_y, right_max_x, right_max_y = right_polygon.bounds
    overlap_x = min(left_max_x, right_max_x) - max(left_min_x, right_min_x)
    overlap_y = min(left_max_y, right_max_y) - max(left_min_y, right_min_y)
    return overlap_x, overlap_y
```

Keep the existing projection plus local legality restoration structure, but make every overlap computation compatible with non-rectangular active components.

- [ ] **Step 4: Re-run the optimizer and CLI tests**

Run the same pytest command.

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  optimizers/repair.py \
  tests/optimizers/test_repair.py \
  tests/cli/test_cli_end_to_end.py
git commit -m "fix: support mixed-shape repair for s1_typical"
```

## Task 6: Update Docs And Run End-To-End Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the README update**

Document the new active benchmark behavior in the mainline overview.

```md
- `s1_typical` now uses a mixed-shape, semantically guided layout generator.
- representative pages render real component footprints instead of rectangle bounds only.
- optimizer repair remains compatible with the official mixed-shape benchmark case.
```

- [ ] **Step 2: Run the focused verification suite**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx pytest \
  tests/schema/test_s1_typical_template.py \
  tests/generator/test_layout_engine.py \
  tests/generator/test_layout_metrics.py \
  tests/visualization/test_case_pages.py \
  tests/optimizers/test_repair.py \
  tests/cli/test_cli_end_to_end.py -v
```

Expected:

- PASS

- [ ] **Step 3: Run the benchmark case smoke flow**

Run:

```bash
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main validate-scenario-template --template scenarios/templates/s1_typical.yaml
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main generate-case --template scenarios/templates/s1_typical.yaml --seed 11 --output-root ./scenario_runs/generated_cases/s1_typical/seed-11
/home/hymn/miniconda3/bin/conda run -n msfenicsx python -m core.cli.main solve-case --case ./scenario_runs/generated_cases/s1_typical/seed-11/s1_typical-seed-0011.yaml --output-root ./scenario_runs
```

Expected:

- all commands exit `0`
- generated case includes mixed shapes and layout semantics
- representative bundle artifacts are still produced successfully

- [ ] **Step 4: Review the diff for unintended changes**

Run:

```bash
git status --short
git diff -- README.md scenarios/templates/s1_typical.yaml core/generator/layout_engine.py \
  core/solver/field_export.py visualization/case_pages.py optimizers/repair.py
```

Expected:

- only intended layout-realism changes remain

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document s1_typical layout realism update"
```
