# Optimization Variable Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前二维热案例建立显式可优化变量注册表，并把它接入 validator 与 LLM prompt。

**Architecture:** 新增 `optimization/variable_registry.py` 作为当前案例的允许改动集与元数据来源。validator 改为使用注册表校验路径和边界，prompt builder 改为向模型暴露允许变量说明。

**Tech Stack:** Python, pytest

---

### Task 1: 写失败测试，固定变量注册表接口

**Files:**
- Create: `/home/hymn/msfenicsx/tests/test_variable_registry.py`

- [ ] **Step 1: 写失败测试，要求注册表包含首批 6 个变量**
- [ ] **Step 2: 运行测试确认失败**

### Task 2: 接入 validator

**Files:**
- Modify: `/home/hymn/msfenicsx/src/validation/proposals.py`
- Modify: `/home/hymn/msfenicsx/tests/test_proposal_validation.py`

- [ ] **Step 1: 写失败测试，要求未注册路径会被拒绝**
- [ ] **Step 2: 写失败测试，要求已注册热源变量能通过**
- [ ] **Step 3: 运行测试确认失败**
- [ ] **Step 4: 最小实现变量级校验**
- [ ] **Step 5: 运行测试确认通过**

### Task 3: 接入 LLM prompt

**Files:**
- Modify: `/home/hymn/msfenicsx/src/llm_adapters/dashscope_qwen.py`
- Modify: `/home/hymn/msfenicsx/tests/test_dashscope_adapter.py`

- [ ] **Step 1: 写失败测试，要求 prompt 包含 editable variable registry**
- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 最小实现 prompt 注入**
- [ ] **Step 4: 运行测试确认通过**
