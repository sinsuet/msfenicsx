# Design Domain Constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给状态增加显式 `design_domain`，并让 proposal validator 基于设计域而不是当前组件包络做几何合法性判断。

**Architecture:** 扩展 state schema 与 baseline YAML，随后更新 validation 模块读取 `geometry.design_domain`。保持 compiler 与 solver 不依赖该字段，让本次改动聚焦在约束层。

**Tech Stack:** Python, pytest, PyYAML

---

### Task 1: 用失败测试锁定 design_domain 行为

**Files:**
- Modify: `/home/hymn/msfenicsx/tests/test_state_schema.py`
- Modify: `/home/hymn/msfenicsx/tests/test_proposal_validation.py`

- [ ] **Step 1: 写失败测试，要求 baseline state 包含 `design_domain`**
- [ ] **Step 2: 写失败测试，要求位于 `design_domain` 内的 spreader 增高可以通过**
- [ ] **Step 3: 运行测试确认失败**

### Task 2: 扩展 state schema 与 baseline

**Files:**
- Modify: `/home/hymn/msfenicsx/src/thermal_state/schema.py`
- Modify: `/home/hymn/msfenicsx/src/thermal_state/load_save.py`
- Modify: `/home/hymn/msfenicsx/states/baseline_multicomponent.yaml`

- [ ] **Step 1: 增加 `DesignDomainState`**
- [ ] **Step 2: 在 state 中接入 `geometry.design_domain`**
- [ ] **Step 3: 更新 baseline YAML**
- [ ] **Step 4: 运行测试确认通过**

### Task 3: 让 validator 使用显式 design_domain

**Files:**
- Modify: `/home/hymn/msfenicsx/src/validation/proposals.py`
- Modify: `/home/hymn/msfenicsx/src/validation/bounds.py`
- Modify: `/home/hymn/msfenicsx/src/validation/geometry.py`

- [ ] **Step 1: 读取 `state.geometry.design_domain`**
- [ ] **Step 2: 位置步长改为按设计域宽高计算**
- [ ] **Step 3: 越界判断改为按设计域判断**
- [ ] **Step 4: 运行测试确认通过**

### Task 4: 文档与真实回归

**Files:**
- Modify: `/home/hymn/msfenicsx/notes/03_llm_optimization_workflow.md`

- [ ] **Step 1: 补充 design_domain 说明**
- [ ] **Step 2: 运行全量测试**
- [ ] **Step 3: 用真实 DashScope 跑 2 轮，观察先前被包络拦住的提案是否能更合理推进**
