# MsGalaxy

MsGalaxy 当前主线已收敛为同仓 `mass` 单栈 scenario runtime。活跃执行链只保留：

- `shell + aperture + catalog components`
- deterministic seed
- `pymoo` search-space factory
- 默认稳定模式 `position_only`
- 实验 opt-in 模式 `operator_program / hybrid`
- STEP 导出
- canonical-only COMSOL
- 稳定审计产物 `summary.json / report.md / result_index.json`

## 当前入口
```powershell
python run/run_scenario.py --stack mass --scenario optical_remote_sensing_bus
```

查看解析结果：

```powershell
python run/run_scenario.py --stack mass --scenario optical_remote_sensing_bus --dry-run
```

## 当前主链真相
- 唯一活跃 scenario 是 `optical_remote_sensing_bus`
- `config/system/mass/base.yaml` 默认 `optimization.search_space_mode = position_only`
- 活跃 `cg_limit` 阈值现为 `max_cg_offset_mm = 30.0`
- 默认稳定主线只开放 `position(x, y, z)`
- `mount_face / aperture / orientation` 由 deterministic seed 固定
- 显式 `shell_contact_required=true` 的场景实例会在搜索期保持法向挂载，不允许优化结果把真实安装件漂离 shell
- `operator_program / hybrid` 已接回 `mass` 主线，但当前生命周期都是 `experimental`
- `operator_program` 的固定语义现为 `operator_program -> PlacementContractGuard projection`
- `hybrid` 的固定语义是 `position -> operator_program -> contract guard projection`
- `ScenarioRuntime` 已改为阶段化状态机：
  - `seed_built -> proxy_optimized -> proxy_feasible -> step_exported -> comsol_model_built -> comsol_solved -> fields_exported`
- `proxy_feasible` 是进入 COMSOL 的硬闸门
- `SatelliteLikenessGate` 现已接入主线，并在 `proxy_feasible` 之后、`STEP/COMSOL` 之前执行
- 默认 `satellite_likeness_gate_mode = strict`
- aperture 对齐载荷的 `payload_face` 现优先使用 `placement_state.mount_face` 真值解析，避免被位置分数误判到侧面组件
- 成功态真实 COMSOL run 默认会保存 `.mph`
- `status / execution_success` 表示主线执行链是否跑通，`real_feasible` 单独表达真实物理是否过约束
- `summary.json / report.md / result_index.json` 现会额外沉淀：
  - `search_space_mode / search_space_lifecycle / optimizer_metadata`
  - `operator_action_sequence / operator_action_families`
  - `contract_guard_hits / contract_guard_reasons`
  - `satellite_likeness_gate_mode / satellite_likeness_gate_passed`
  - `satellite_layout_candidate / satellite_likeness_report`
  - `shell_contact_audit / component_thermal_audit / dominant_thermal_hotspot`
- 失败路径也会稳定写出：
  - `summary.json`
  - `report.md`
  - `result_index.json`

## Search Space Mode

默认配置位于 `config/system/mass/base.yaml`：

```yaml
optimization:
  search_space_mode: position_only
```

当前支持三种模式：

- `position_only`
  - 默认稳定主线
  - `variable_coverage = ["position"]`
- `operator_program`
  - 实验模式
  - `variable_coverage = ["operator_program"]`
  - 固定语义：`operator_program -> PlacementContractGuard projection`
- `hybrid`
  - 实验模式
  - `variable_coverage = ["position", "operator_program"]`
  - 固定语义：`position -> operator_program -> PlacementContractGuard projection`

算法流程、约束处理、领域算子执行位置以及最新真实案例解读，可参考：

- `docs/guides/2026-03-25-mass-nsgaii-hybrid-search-space-explainer.md`

边界说明：

- `mount_face / aperture / orientation` 仍不开放为搜索变量
- `CentroidPushApartRepair` 只允许绑定 `position_only`
- 当前已完成 `operator_program / hybrid` 的主线 artifact 合同接线
- `operator_program` 已在受控预算下完成 `seed=42` 的一条 real COMSOL chain 到 `fields_exported`
- `hybrid` 已在受控预算下完成 `seed=42,43,44` 三条 real COMSOL chain 到 `fields_exported`
- 还不能把 `operator_program / hybrid` 的结果表述为真实 COMSOL validated gain

默认运行：

```powershell
python run/run_scenario.py --stack mass --scenario optical_remote_sensing_bus
```

若要试验 `hybrid`，请通过覆盖 base config 显式 opt-in：

```yaml
optimization:
  search_space_mode: hybrid
  hybrid_n_action_slots: 1
  pymoo_pop_size: 4
  pymoo_n_gen: 1
```

```powershell
python run/run_scenario.py --stack mass --scenario optical_remote_sensing_bus --base-config path/to/mass-hybrid.yaml --run-label hybrid_proxy_smoke
```

## 几何与物理合同
- 搜索代理几何、种子几何、STEP 导出几何已统一到同一条 geometry truth chain
- `payload_camera` 当前有效搜索包络为 `140 x 120 x 170 mm`
- `payload_camera` 目录件现补齐 `4` 个安装柱 + `4` 个 shell contact pad，在不遮挡 `camera_window` 的前提下提供真实挂载接触界面
- `antenna_panel` 在 `+Y` 安装朝向下有效包络为 `120 x 8 x 60 mm`
- `optical_remote_sensing_microsat.optical_avionics_middeck` 当前允许 `communication` 类侧装天线面板通过 zone grammar
- COMSOL 主线只保留 canonical profile
- 默认 `shell mount contact` 现在只会绑定 Union 几何上的真实共享内边界，不再把 shell/component 两侧 box-selection 直接并集后喂给 COMSOL
- `requested_profile == effective_profile` 只代表请求未降级，不等于“所有物理场已真正求解完成”
- source claim 现已区分：
  - `canonical_request_preserved`
  - `*_setup_ok`
  - `*_study_entered`
  - `*_study_solved`

## 当前状态说明
- 活跃主线只保留 `mass`
- `agent_loop` / `vop_maas` / 旧 L1-L4 入口 / review-package / Blender sidecar / teacher-demo 已退出活跃代码面并归档
- `tools/comsol_field_demo/tool_real_comsol_vertical_smoke.py` 已重接为受控 smoke harness，复用当前主线公共模块
- 当前可以宣称：
  - canonical-only request 链已通
  - STEP 几何链已通
  - COMSOL model-build / solve / field-export 链已通
  - 主线已能把真实热热点定位到具体组件
  - 主线已能把 shell/contact 是否存在真实共享界面写入审计产物
- 当前可以额外诚实宣称：
  - `optical_remote_sensing_bus` 已在 2026-03-24 三次独立复跑中稳定得到 `satellite_likeness_gate_passed=true` 与 `real_feasible=true`
  - 上述三次复跑都稳定产出 `STEP + mph + fields`
- 当前也可以诚实宣称：
  - `operator_program / hybrid` 已正式接入 `mass` 主线 artifact 合同
  - 默认行为仍保持 `position_only`
  - `operator_program` 现已可稳定写出 `search_space_mode / optimizer_metadata / operator_action_sequence / contract_guard_hits`
  - `operator_program` 已有一条受控 real COMSOL run 到达 `fields_exported`
  - `hybrid` 现已可稳定写出 `search_space_mode / optimizer_metadata / operator_action_sequence / contract_guard_hits`
  - `hybrid` 已有三条受控 real COMSOL run 到达 `fields_exported`
- 当前还不能宣称：
  - 跨环境/跨种子意义上的 release-grade 稳定性
  - 场景矩阵级通过能力
  - `operator_program / hybrid` 已获得真实 COMSOL validated 结论
- 最新真实主线证据（2026-03-24）显示：
  - `execution_success=true`
  - `real_feasible=true`
  - `dominant_thermal_hotspot = payload_camera`
  - `payload_camera.max_temp_c ≈ 50.10 degC`
  - `shell_contact_audit.payload_camera.selection_status = shared_interface_applied`
  - `shell_contact_audit.applied_count = 5`
  - `shell_contact_audit.unresolved_count = 0`
  - 该次 run 稳定产出：
    - `STEP`
    - `.mph`
    - `temperature/stress/displacement fields`
  - 这说明当前热点主因确实是几何上缺少真实导热挂载界面；补齐真实安装接触几何后，主线热可行性已经回到约束内
- 本轮 COMSOL 语义修正参考官方文档：
  - [Thermal Contact](https://doc.comsol.com/6.3/doc/com.comsol.help.heat/heat_ug_ht_features.09.092.html)
  - [Identity Pair](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_ref_definitions.21.110.html)
  - [Pairs in Physics Interfaces](https://doc.comsol.com/6.2/doc/com.comsol.help.comsol/comsol_ref_definitions.19.029.html)

## 关键文件
- `run/run_scenario.py`
- `workflow/scenario_runtime.py`
- `domain/satellite/scenario.py`
- `domain/satellite/seed.py`
- `geometry/catalog_geometry.py`
- `geometry/cad_export_occ.py`
- `simulation/comsol_driver.py`
- `simulation/comsol/physics_profiles.py`
- `api/cli.py`
- `api/server.py`

## 验证
```powershell
python -m pytest tests -q
```

当前仓库状态下，2026-03-12 本轮结果为：

- `190 passed`
- `3 skipped`

2026-03-24 本轮与卫星 gate 修复直接相关的定向验证为：

- `python -m pytest tests/test_satellite_runtime.py tests/test_scenario_runtime_contract.py tests/test_comsol_physics_profiles.py tests/test_satellite_seed.py tests/test_run_scenario_cli.py -q`
- `22 passed`

2026-03-24 本轮 search-space integration 定向验证为：

- `python -m pytest tests/test_mass_search_space_factory.py tests/test_contract_guard.py tests/test_hybrid_codec.py tests/test_scenario_runtime_contract.py tests/test_satellite_runtime.py tests/test_run_scenario_cli.py -q`
- `27 passed`

2026-03-24 本轮 `run_scenario` dry-run 成功返回 `base_config = config/system/mass/base.yaml`。

2026-03-24 本轮 `hybrid` proxy smoke（`experiments/20260324/181010_mass_hybrid_proxy_smoke`）结果为：

- `status=FAILED`
- `execution_stage=proxy_optimized`
- `search_space_mode=hybrid`
- `search_space_lifecycle=experimental`
- `comsol_attempted=false`
- `comsol_block_reason=proxy_infeasible`
- `operator_action_sequence=["cg_recenter"]`
- `operator_action_families=["geometry"]`

2026-03-24 本轮默认 `position_only` 主线两次独立真实复跑：

- `experiments/20260324/194254_mass_rerun_real_chain_1_20260324`
- `experiments/20260324/194512_mass_rerun_real_chain_2_20260324`
- 两次都为：
  - `status=SUCCESS`
  - `execution_stage=fields_exported`
  - `real_feasible=true`
  - `max_temp≈50.0489 degC`

2026-03-24 本轮受控 `operator_program` real COMSOL run（`experiments/20260324/224057_mass_operator_program_real_chain_guardfix_20260324`）结果为：

- `status=SUCCESS`
- `search_space_mode=operator_program`
- `execution_stage=fields_exported`
- `real_feasible=true`
- `operator_action_sequence=["cg_recenter"]`
- `contract_guard_hits=6`
- `contract_guard_reasons=["semantic_zone_bounds","mount_axis_locked"]`
- `shell_contact_audit.applied_count=5`
- `shell_contact_audit.unresolved_count=0`
- `max_temp≈49.8628 degC`

2026-03-24 本轮受控 `hybrid` real COMSOL run（`experiments/20260324/194725_mass_hybrid_real_chain_20260324`）结果为：

- `status=SUCCESS`
- `search_space_mode=hybrid`
- `execution_stage=fields_exported`
- `real_feasible=true`
- `operator_action_sequence=["cg_recenter"]`
- `contract_guard_hits=4`
- `max_temp≈50.0085 degC`

2026-03-24 本轮 `hybrid` 额外两次受控真实复跑：

- `experiments/20260324/205121_mass_hybrid_real_chain_s43_20260324`
- `experiments/20260324/205301_mass_hybrid_real_chain_s44_20260324`
- 两次都为：
  - `status=SUCCESS`
  - `search_space_mode=hybrid`
  - `execution_stage=fields_exported`
  - `real_feasible=true`
  - `operator_action_sequence=["cg_recenter"]`

## 仍需继续
- 继续围绕 `optical_remote_sensing_bus` 做独立复跑与 artifact 审计，确认这次 `real_feasible=true` 结果可重复
- 在该场景通过“重复可行 + stable artifacts”前，不扩场景矩阵
- 在不影响默认 `position_only` 主线的前提下，对 `operator_program / hybrid` 做匹配预算的 proxy 对照和多 seed 统计
