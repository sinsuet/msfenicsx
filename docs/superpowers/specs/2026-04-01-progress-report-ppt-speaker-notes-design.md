# Progress Report PPT Speaker Notes Design

**Date:** 2026-04-01

## Goal

为已经从 Beamer 转换得到的 PowerPoint 成品 `C:\Users\hymn\Downloads\main.pptx` 生成一套完整的中文逐页演讲备注，并把备注直接写入 PowerPoint 的 speaker notes 中，输出一个不覆盖原件的新文件。

## Context

- 当前目标文件共有 35 页。
- 用户要求备注风格为“详细逐页讲稿型”。
- 目标汇报时长约 25 分钟。
- 当前机器无法稳定使用 PowerPoint COM 自动化，因此不能依赖桌面 PowerPoint 直接写 notes。
- 当前 `pptx` 内部还没有 `notesSlides` 或 `notesMaster` 结构，因此需要补齐最小可用的 notes OpenXML 结构。

## Content Design

### Remarks Style

每页备注采用统一结构：

1. 建议时长
2. 本页主讲口径
3. 自然转场

正文页备注按可直接口播的连续自然段撰写，不只给关键词。Backup 页备注则改为“若被问到可这样回答”的简洁答辩口径。

### Timing Strategy

- 标题/路线页：15 到 25 秒
- 问题定义与框架页：35 到 55 秒
- 关键实验页：40 到 70 秒
- 结论页：30 到 45 秒
- Backup 页：10 到 20 秒，默认不主动展开

目标不是机械平均每页时长，而是让主线正文控制在约 20 到 21 分钟，为现场停顿、补充说明和互动留出约 4 到 5 分钟余量。

## Technical Design

### File Strategy

保留原始文件：

- `C:\Users\hymn\Downloads\main.pptx`

生成新文件：

- `C:\Users\hymn\Downloads\main_with_notes.pptx`

并在仓库中保留可重生成的源文件与脚本：

- `docs/reports/ppt_notes/2026-04-01-progress-report-notes/speaker_notes.json`
- `docs/reports/ppt_notes/2026-04-01-progress-report-notes/inject_notes.py`
- `docs/reports/ppt_notes/2026-04-01-progress-report-notes/extract_notes.py`

### Notes Injection Approach

不重建整份 deck，也不修改页面版式。只对现有 `pptx` 做 OpenXML 级别的 notes 注入：

1. 复制原始 `pptx` 为新文件
2. 为新文件补充 `notesMaster` 与相关 relationship
3. 为每页 slide 创建对应的 `notesSlide`
4. 在 slide relation 中挂接 `notesSlide`
5. 更新 `[Content_Types].xml`
6. 把逐页讲稿文本写入 notes 占位结构

### Validation

验证分三层：

1. 结构验证：确认输出文件包含 35 个 `notesSlides`
2. 内容验证：抽取若干页备注文本，确认与源文件一致
3. 使用验证：确保结果文件可被 PowerPoint 正常打开

## Constraints

- 不覆盖原始 `main.pptx`
- 不调整任何现有页面视觉内容
- 不发明超出已有四篇报告与当前 deck 证据边界的新结论
- 对 `LLM-union` 的表述继续保持当前 deck 的克制口径

## Expected Outcome

交付一份可以直接在 PowerPoint 演讲者视图中使用的 `main_with_notes.pptx`，并保留一套可再次编辑和重生成备注的仓库内源文件。
