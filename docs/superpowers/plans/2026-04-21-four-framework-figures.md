# Four Framework Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create four standalone TikZ framework figures under `paper/latex/build/tikzz/` that match the palette and visual language of `method_architecture_a1.tex`, compile each figure in isolation, and keep manuscript insertion separate from figure production.

**Architecture:** First extract a shared TikZ style module so all four figures inherit the same palette, card shapes, arrow language, and typography. Then implement one standalone source per figure: fixed-boundary modes, inline control loop, taxonomy-recovery map, and evidence asset map. Each figure compiles to its own PDF in `paper/latex/build/tikzz/`; this plan does not modify `paper/latex/sections/zh/*.tex`.

**Tech Stack:** XeLaTeX, TikZ/PGF, `standalone` class, shared TikZ style input, direct compile-based verification.

**Spec:** [docs/superpowers/specs/2026-04-21-zh-evidence-pass-design.md](../specs/2026-04-21-zh-evidence-pass-design.md)

---

## File Map

**Create:**
- `paper/latex/build/tikzz/framework_figure_style.tex` — shared TikZ libraries, palette, rounded panel/card styles, arrow styles, title/note typography.
- `paper/latex/build/tikzz/fixed_boundary_modes_a1.tex` — Figure 1: fixed optimization boundary + raw/union/llm comparison figure.
- `paper/latex/build/tikzz/inline_control_loop_a1.tex` — Figure 2: inline control loop flow figure.
- `paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex` — Figure 3: collapse taxonomy ↔ layered recovery mapping figure.
- `paper/latex/build/tikzz/evidence_asset_map_a1.tex` — Figure 4: experimental evidence asset map figure.

**Verify:**
- `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf`
- `paper/latex/build/tikzz/inline_control_loop_a1.pdf`
- `paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf`
- `paper/latex/build/tikzz/evidence_asset_map_a1.pdf`

**Reference Only:**
- `paper/latex/build/tikzz/method_architecture_a1.tex` — visual anchor for palette, rounded white cards, blue/orange panels, restrained accent routing.

---

### Task 1: Create the shared TikZ style module

**Files:**
- Create: `paper/latex/build/tikzz/framework_figure_style.tex`
- Verify: `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf`

- [ ] **Step 1: Write the shared style source**

Create `paper/latex/build/tikzz/framework_figure_style.tex` with this exact content:

```tex
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc,backgrounds,shapes.geometric,shapes.multipart}

\definecolor{panelblueborder}{HTML}{3A86C8}
\definecolor{panelbluefill}{HTML}{EAF3FB}
\definecolor{panelorangeborder}{HTML}{E67E22}
\definecolor{panelorangefill}{HTML}{FDF1E3}
\definecolor{feedbackpurple}{HTML}{8E44AD}
\definecolor{routegray}{HTML}{333333}
\definecolor{lightgraydash}{HTML}{CFCFCF}
\definecolor{softgreenborder}{HTML}{2F855A}
\definecolor{softgreenfill}{HTML}{E8F5EC}
\definecolor{softredborder}{HTML}{C05621}
\definecolor{softredfill}{HTML}{FDEEE7}

\tikzset{
  panel/.style={rounded corners=7pt, very thick, inner sep=14pt},
  mainpanel/.style={panel, draw=panelblueborder, fill=panelbluefill},
  sidepanel/.style={panel, draw=panelorangeborder, fill=panelorangefill},
  supportpanel/.style={panel, draw=softgreenborder, fill=softgreenfill},
  warnpanel/.style={panel, draw=softredborder, fill=softredfill},
  card/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=4.2cm, minimum height=1.15cm, align=center, line width=0.8pt},
  widecard/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=5.9cm, minimum height=1.25cm, align=center, line width=0.8pt},
  smallcard/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=3.1cm, minimum height=1.02cm, align=center, line width=0.8pt},
  tinycard/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=2.45cm, minimum height=0.90cm, align=center, line width=0.8pt},
  flow/.style={-Latex, line width=1.0pt, draw=routegray},
  accentflow/.style={-Latex, line width=1.0pt, draw=panelblueborder},
  supportflow/.style={-Latex, line width=1.0pt, draw=panelorangeborder},
  feedback/.style={-Latex, line width=1.0pt, draw=feedbackpurple, dashed},
  mutedlink/.style={line width=0.9pt, draw=lightgraydash, dashed},
  titlelabel/.style={font=\bfseries\Large},
  sectionlabel/.style={font=\bfseries\large},
  note/.style={align=left, font=\small, text width=5.2cm},
  shortnote/.style={align=left, font=\small, text width=3.2cm},
  centertext/.style={align=center, font=\small},
  policynote/.style={draw=none, fill=white, inner sep=1pt, font=\small, text=routegray}
}
```

- [ ] **Step 2: Create a one-line smoke file to verify the shared style can be imported**

Create `paper/latex/build/tikzz/fixed_boundary_modes_a1.tex` temporarily with this smoke content:

```tex
\documentclass[tikz,border=8pt]{standalone}
\input{framework_figure_style}

\begin{document}
\begin{tikzpicture}
  \node[card] {framework style smoke test};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 3: Compile the smoke file to verify the shared style loads cleanly**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
```

Expected: PASS and `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf` exists.

- [ ] **Step 4: Commit the shared style module before building real figures**

```bash
git add paper/latex/build/tikzz/framework_figure_style.tex paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
git commit -m "docs: add shared tikz framework figure styles"
```

### Task 2: Build Figure 1 — fixed optimization boundary and mode comparison

**Files:**
- Modify: `paper/latex/build/tikzz/fixed_boundary_modes_a1.tex`
- Verify: `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf`

- [ ] **Step 1: Replace the smoke file with the real Figure 1 source**

Overwrite `paper/latex/build/tikzz/fixed_boundary_modes_a1.tex` with this source:

```tex
\documentclass[tikz,border=8pt]{standalone}
\input{framework_figure_style}

\begin{document}
\begin{tikzpicture}[node distance=0.66cm and 1.00cm]
  \node[titlelabel, text=panelblueborder, anchor=west] (lefttitle) at (0,5.55) {Fixed Optimization Boundary};

  \node[widecard, minimum height=1.48cm, below=0.42cm of lefttitle.west, anchor=west] (repr) {
    \textbf{Shared Representation}\\
    layout variables + sink boundary variables
  };

  \node[widecard, minimum height=1.48cm, below=0.56cm of repr] (ops) {
    \textbf{Shared Semantic Operator Pool}\\
    unified action families + candidate manipulation primitives
  };

  \node[widecard, minimum height=1.58cm, below=0.56cm of ops] (eval) {
    \textbf{Shared Repair / Evaluation Pipeline}\\
    geometry repair $\rightarrow$ cheap constraints $\rightarrow$ expensive numerical evaluation
  };

  \begin{scope}[on background layer]
    \node[mainpanel, fit=(repr)(ops)(eval), inner xsep=19pt, inner ysep=18pt] (mainpanelbox) {};
  \end{scope}

  \node[smallcard, anchor=north] (raw) at ($(mainpanelbox.south west)+(1.35,-1.42)$) {
    \textbf{raw}\\baseline evolutionary\\scheduling
  };
  \node[smallcard, draw=panelorangeborder, anchor=north] (union) at ($(mainpanelbox.south)+(0,-1.42)$) {
    \textbf{union}\\non-LLM unified\\semantic scheduling
  };
  \node[smallcard, draw=feedbackpurple, dashed, anchor=north] (llm) at ($(mainpanelbox.south east)+(-1.35,-1.42)$) {
    \textbf{llm}\\state-guided online\\controller scheduling
  };
  \node[policynote, anchor=north] (ctrlcaption) at ($(union.south)+(0,-0.22)$) {Only the controller layer changes across modes};

  \node[titlelabel, text=panelorangeborder, anchor=west] (righttitle) at ($(mainpanelbox.north east)+(0.72,-0.02)$) {Fair Comparison Constraints};
  \node[sidepanel, anchor=north west, minimum width=6.10cm, minimum height=4.18cm] (sidebox) at ($(righttitle.south west)+(0,-0.24)$) {};
  \node[note, anchor=north west] at ($(sidebox.north west)+(0.34,-0.40)$) {
    \textbf{Held fixed across raw / union / llm}\\[3pt]
    $\bullet$ representation and decision encoding\\
    $\bullet$ semantic operator registry\\
    $\bullet$ repair, cheap filtering, solver evaluation\\
    $\bullet$ optimization budget and stopping rule\\[7pt]
    \textbf{Variable part}\\
    controller policy for action scheduling and phase emphasis
  };

  \draw[flow] (repr) -- (ops);
  \draw[flow] (ops) -- (eval);
  \draw[accentflow] (raw.north) -- ++(0,0.68) -| ($(mainpanelbox.south)+(-2.55,0.03)$);
  \draw[accentflow] (union.north) -- ++(0,0.94) -- ($(mainpanelbox.south)+(0,0.03)$);
  \draw[accentflow] (llm.north) -- ++(0,0.68) -| ($(mainpanelbox.south)+(2.55,0.03)$);
  \draw[feedback] ($(eval.east)+(0.06,0.12)$) .. controls +(1.72,0.10) and +(0.18,1.18) .. ($(llm.north)+(0.00,0.34)$);
  \draw[mutedlink] ($(mainpanelbox.north east)+(0.18,-0.22)$) -- ($(sidebox.north west)+(-0.10,-0.16)$);
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Compile Figure 1**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
```

Expected: PASS and `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf` is readable.

- [ ] **Step 3: Check Figure 1 against visual requirements and make only spacing/routing edits if needed**

Review these requirements:

```text
- left blue panel reads as the shared optimization backbone
- right orange panel reads as comparison constraints, not another pipeline
- raw / union / llm visually read as controller variants
- internal cards remain white and rounded
- arrows are restrained and not overly decorative
```

Allowed adjustments are limited to values already in the file such as:

```tex
node distance=0.66cm and 1.00cm
minimum width=6.10cm
minimum height=4.18cm
inner xsep=19pt
inner ysep=18pt
```

- [ ] **Step 4: Recompile Figure 1 after any spacing changes**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
```

Expected: PASS and updated PDF.

- [ ] **Step 5: Commit Figure 1**

```bash
git add paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
git commit -m "docs: add fixed boundary framework figure"
```

### Task 3: Build Figure 2 — inline control loop

**Files:**
- Create: `paper/latex/build/tikzz/inline_control_loop_a1.tex`
- Verify: `paper/latex/build/tikzz/inline_control_loop_a1.pdf`

- [ ] **Step 1: Write the standalone Figure 2 source**

Create `paper/latex/build/tikzz/inline_control_loop_a1.tex` with this exact content:

```tex
\documentclass[tikz,border=8pt]{standalone}
\input{framework_figure_style}

\begin{document}
\begin{tikzpicture}[node distance=0.64cm and 0.82cm]
  \node[titlelabel, text=panelblueborder, anchor=west] (title) at (0,4.75) {Inline Control Loop};

  \node[card, minimum width=3.45cm, minimum height=1.18cm, below=0.44cm of title.west, anchor=west] (state) {
    \textbf{State Summary}\\
    compressed progress + layout context
  };
  \node[card, minimum width=3.45cm, minimum height=1.18cm, right=0.78cm of state] (ctrl) {
    \textbf{Controller Decision}\\
    phase emphasis + action preference
  };
  \node[card, minimum width=3.45cm, minimum height=1.18cm, right=0.78cm of ctrl] (cand) {
    \textbf{Candidate Generation}\\
    apply scheduled operator family
  };
  \node[card, minimum width=3.45cm, minimum height=1.18cm, right=0.78cm of cand] (repair) {
    \textbf{Repair / Cheap Filter}\\
    legality restoration + cheap rejection
  };
  \node[card, minimum width=3.65cm, minimum height=1.18cm, right=0.78cm of repair] (eval) {
    \textbf{Expensive Evaluation}\\
    solver-backed numerical assessment
  };

  \node[sidepanel, fit=(state)(ctrl)(cand)(repair)(eval), inner xsep=18pt, inner ysep=16pt] (loopbox) {};

  \node[supportpanel, minimum width=4.55cm, minimum height=1.65cm, anchor=north west] (recoverbox) at ($(loopbox.south west)+(0.15,-2.10)$) {};
  \node[sectionlabel, text=softgreenborder, anchor=west] at ($(recoverbox.north west)+(0.24,-0.33)$) {Layered Recovery Interventions};
  \node[shortnote, anchor=north west] at ($(recoverbox.north west)+(0.26,-0.75)$) {
    semantic / spatial / intent / retrieval / saturation recovery act by correcting the state, the retrieved context, or the outgoing control preference.
  };

  \draw[flow] (state) -- (ctrl);
  \draw[flow] (ctrl) -- (cand);
  \draw[flow] (cand) -- (repair);
  \draw[flow] (repair) -- (eval);
  \draw[feedback] (eval.south) .. controls +(0,-1.45) and +(0,-1.45) .. (state.south);
  \draw[supportflow] (recoverbox.north) -- ++(0,0.52) -| ($(ctrl.south)+(0,-0.02)$);
  \draw[supportflow] ($(recoverbox.north east)+(-0.25,0.00)$) -- ++(0,0.52) -| ($(state.south)+(0,-0.02)$);

  \node[policynote, anchor=south] at ($(state.north)!0.5!(eval.north)+(0,0.52)$) {one iteration: $s_t \rightarrow u_t \rightarrow \Phi(\mathbf{x}_t, s_t, u_t) \rightarrow s_{t+1}$};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Compile Figure 2**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/inline_control_loop_a1.tex
```

Expected: PASS and `paper/latex/build/tikzz/inline_control_loop_a1.pdf` exists.

- [ ] **Step 3: Verify the loop reads left-to-right with a clear feedback return path**

Check these requirements:

```text
- five main white cards appear in one left-to-right loop
- dashed purple feedback path is clearly visible
- green recovery box reads as intervention support, not another pipeline stage
- formula note stays secondary and does not dominate the figure
```

If needed, only adjust values already present in the file, such as card widths, horizontal gaps, or curve control offsets.

- [ ] **Step 4: Recompile Figure 2 after any layout polish**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/inline_control_loop_a1.tex
```

Expected: PASS and updated PDF.

- [ ] **Step 5: Commit Figure 2**

```bash
git add paper/latex/build/tikzz/inline_control_loop_a1.tex
git commit -m "docs: add inline control loop figure"
```

### Task 4: Build Figure 3 — collapse taxonomy and layered recovery map

**Files:**
- Create: `paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex`
- Verify: `paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf`

- [ ] **Step 1: Write the standalone Figure 3 source**

Create `paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex` with this exact content:

```tex
\documentclass[tikz,border=8pt]{standalone}
\input{framework_figure_style}

\begin{document}
\begin{tikzpicture}[node distance=0.46cm and 1.20cm]
  \node[titlelabel, text=panelblueborder, anchor=west] (lefttitle) at (0,5.35) {Collapse Taxonomy};
  \node[titlelabel, text=softgreenborder, anchor=west] (righttitle) at (8.45,5.35) {Layered Recovery};

  \node[card, minimum width=5.35cm, anchor=west] (c1) at (0,4.35) {\textbf{Semantic Misalignment}\\phase need and action meaning no longer align};
  \node[card, minimum width=5.35cm, below=0.42cm of c1.west, anchor=west] (c2) {\textbf{Spatial Blindness}\\compressed state misses key geometric tension};
  \node[card, minimum width=5.35cm, below=0.42cm of c2.west, anchor=west] (c3) {\textbf{Objective-Intent Drift}\\multi-objective focus dilutes across repeated decisions};
  \node[card, minimum width=5.35cm, below=0.42cm of c3.west, anchor=west] (c4) {\textbf{History-Retrieval Failure}\\key trajectory evidence fails to return to the window};
  \node[card, minimum width=5.35cm, below=0.42cm of c4.west, anchor=west] (c5) {\textbf{Late-Stage Saturation}\\high-frequency low-yield preference repetition persists};

  \node[card, minimum width=5.35cm, draw=softgreenborder, anchor=west] (r1) at (8.45,4.35) {\textbf{Semantic-Layer Recovery}\\restore action meaning and phase alignment};
  \node[card, minimum width=5.35cm, draw=softgreenborder, below=0.42cm of r1.west, anchor=west] (r2) {\textbf{Spatial-Layer Recovery}\\re-inject geometric context into the summary};
  \node[card, minimum width=5.35cm, draw=softgreenborder, below=0.42cm of r2.west, anchor=west] (r3) {\textbf{Intent-Layer Recovery}\\re-strengthen target priority structure};
  \node[card, minimum width=5.35cm, draw=softgreenborder, below=0.42cm of r3.west, anchor=west] (r4) {\textbf{Retrieval-Layer Recovery}\\bring back decisive recent trajectory facts};
  \node[card, minimum width=5.35cm, draw=softgreenborder, below=0.42cm of r4.west, anchor=west] (r5) {\textbf{Saturation-Layer Recovery}\\suppress repeated low-yield actions late in search};

  \begin{scope}[on background layer]
    \node[mainpanel, fit=(c1)(c2)(c3)(c4)(c5), inner xsep=15pt, inner ysep=15pt] {};
    \node[supportpanel, fit=(r1)(r2)(r3)(r4)(r5), inner xsep=15pt, inner ysep=15pt] {};
  \end{scope}

  \draw[feedback] (c1.east) -- (r1.west);
  \draw[feedback] (c2.east) -- (r2.west);
  \draw[feedback] (c3.east) -- (r3.west);
  \draw[feedback] (c4.east) -- (r4.west);
  \draw[feedback] (c5.east) -- (r5.west);

  \node[sidepanel, minimum width=4.35cm, minimum height=1.90cm, anchor=north] (legend) at ($(c5.south)!0.5!(r5.south)+(0,-1.28)$) {};
  \node[centertext, anchor=center] at (legend.center) {\textbf{Mapping rule}\\target failure $\rightarrow$ intervention location $\rightarrow$ restored capability};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Compile Figure 3**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex
```

Expected: PASS and `paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf` exists.

- [ ] **Step 3: Verify the figure reads as a left-right mapping, not two disconnected lists**

Check these requirements:

```text
- left and right columns are visually balanced
- dashed purple links clearly pair each collapse with its recovery layer
- the bottom legend reads as a summary note, not a third column
- no card text overlaps or crowding
```

Allowed adjustments are limited to card widths, vertical spacing, and the legend box size/position already present in the source.

- [ ] **Step 4: Recompile Figure 3 after any spacing fixes**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex
```

Expected: PASS and updated PDF.

- [ ] **Step 5: Commit Figure 3**

```bash
git add paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex
git commit -m "docs: add taxonomy recovery mapping figure"
```

### Task 5: Build Figure 4 — evidence asset map

**Files:**
- Create: `paper/latex/build/tikzz/evidence_asset_map_a1.tex`
- Verify: `paper/latex/build/tikzz/evidence_asset_map_a1.pdf`

- [ ] **Step 1: Write the standalone Figure 4 source**

Create `paper/latex/build/tikzz/evidence_asset_map_a1.tex` with this exact content:

```tex
\documentclass[tikz,border=8pt]{standalone}
\input{framework_figure_style}

\begin{document}
\begin{tikzpicture}[node distance=0.46cm and 0.92cm]
  \node[titlelabel, text=panelorangeborder, anchor=west] (lefttitle) at (0,5.55) {Compare Report Evidence};
  \node[titlelabel, text=panelblueborder, anchor=west] (righttitle) at (8.20,5.55) {Single-Run Mechanism Evidence};
  \node[titlelabel, text=softgreenborder, anchor=west] (centertitle) at (4.15,2.05) {Experimental Claims};

  \node[smallcard, anchor=west] (l1) at (0,4.55) {summary overview};
  \node[smallcard, below=0.34cm of l1.west, anchor=west] (l2) {progress dashboard};
  \node[smallcard, below=0.34cm of l2.west, anchor=west] (l3) {summary / metrics tables};
  \node[smallcard, below=0.34cm of l3.west, anchor=west] (l4) {temperature / gradient comparisons};

  \node[smallcard, anchor=west] (r1) at (8.20,4.55) {objective progress};
  \node[smallcard, below=0.34cm of r1.west, anchor=west] (r2) {operator-phase heatmap};
  \node[smallcard, below=0.34cm of r2.west, anchor=west] (r3) {layout / representative fields};
  \node[smallcard, below=0.34cm of r3.west, anchor=west] (r4) {trace / prompt / timeline assets};

  \node[card, draw=softgreenborder, minimum width=4.55cm, minimum height=1.10cm, anchor=west] (c1) at (4.15,1.10) {\textbf{Claim A} current cross-mode differences are observable under a fixed boundary};
  \node[card, draw=softgreenborder, minimum width=4.55cm, minimum height=1.10cm, below=0.35cm of c1.west, anchor=west] (c2) {\textbf{Claim B} collapse and recovery leave mechanism-relevant evidence inside the llm trajectory};

  \begin{scope}[on background layer]
    \node[sidepanel, fit=(l1)(l2)(l3)(l4), inner xsep=14pt, inner ysep=14pt] (leftbox) {};
    \node[mainpanel, fit=(r1)(r2)(r3)(r4), inner xsep=14pt, inner ysep=14pt] (rightbox) {};
    \node[supportpanel, fit=(c1)(c2), inner xsep=14pt, inner ysep=14pt] (centerbox) {};
  \end{scope}

  \draw[supportflow] (l1.east) -- (c1.west);
  \draw[supportflow] (l2.east) -- (c1.west);
  \draw[supportflow] (l3.east) -- (c1.west);
  \draw[supportflow] (l4.east) -- (c1.west);

  \draw[accentflow] (r1.west) -- (c2.east);
  \draw[accentflow] (r2.west) -- (c2.east);
  \draw[accentflow] (r3.west) -- (c2.east);
  \draw[accentflow] (r4.west) -- (c2.east);

  \draw[feedback] (c1.east) .. controls +(1.35,0.18) and +(-1.15,0.62) .. (r2.west);
  \draw[feedback] (c2.west) .. controls +(-1.35,-0.18) and +(1.10,-0.62) .. (l2.east);

  \node[policynote, anchor=south] at ($(leftbox.north)!0.5!(rightbox.north)+(0,0.48)$) {compare report answers cross-mode attribution; single-run assets answer mechanism};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Compile Figure 4**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/evidence_asset_map_a1.tex
```

Expected: PASS and `paper/latex/build/tikzz/evidence_asset_map_a1.pdf` exists.

- [ ] **Step 3: Verify the three-zone reading order (left assets → center claims ← right assets)**

Check these requirements:

```text
- orange compare-report block reads as cross-mode evidence
- blue single-run block reads as mechanism evidence
- green center block reads as claim sink, not another source block
- feedback lines suggest mutual support without turning the figure into a loop diagram
```

If needed, only adjust dimensions and link control points that already exist in the file.

- [ ] **Step 4: Recompile Figure 4 after any spacing or routing polish**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/evidence_asset_map_a1.tex
```

Expected: PASS and updated PDF.

- [ ] **Step 5: Commit Figure 4**

```bash
git add paper/latex/build/tikzz/evidence_asset_map_a1.tex
git commit -m "docs: add evidence asset map figure"
```

### Task 6: Final compile sweep and artifact verification

**Files:**
- Verify: `paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf`
- Verify: `paper/latex/build/tikzz/inline_control_loop_a1.pdf`
- Verify: `paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf`
- Verify: `paper/latex/build/tikzz/evidence_asset_map_a1.pdf`

- [ ] **Step 1: Compile all four figures in sequence**

Run:
```bash
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/fixed_boundary_modes_a1.tex && \
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/inline_control_loop_a1.tex && \
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex && \
xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/evidence_asset_map_a1.tex
```

Expected: PASS and four readable PDFs exist.

- [ ] **Step 2: Confirm all generated artifacts stay confined to `paper/latex/build/tikzz/`**

Check for at least these outputs:

```text
paper/latex/build/tikzz/framework_figure_style.tex
paper/latex/build/tikzz/fixed_boundary_modes_a1.tex
paper/latex/build/tikzz/fixed_boundary_modes_a1.pdf
paper/latex/build/tikzz/inline_control_loop_a1.tex
paper/latex/build/tikzz/inline_control_loop_a1.pdf
paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex
paper/latex/build/tikzz/taxonomy_recovery_map_a1.pdf
paper/latex/build/tikzz/evidence_asset_map_a1.tex
paper/latex/build/tikzz/evidence_asset_map_a1.pdf
```

Expected: source and build outputs remain under `paper/latex/build/tikzz/`; no manuscript section files are modified.

- [ ] **Step 3: Record the intended manuscript mapping for later insertion**

Write this mapping into the execution notes or final handoff summary:

```text
- fixed_boundary_modes_a1.pdf -> zh/04_method fixed-boundary comparison figure
- inline_control_loop_a1.pdf -> zh/04_method inline control loop figure
- taxonomy_recovery_map_a1.pdf -> zh/05_collapse_and_recovery taxonomy map figure
- evidence_asset_map_a1.pdf -> zh/06_experiments evidence map figure
```

- [ ] **Step 4: Commit the full four-figure batch**

```bash
git add paper/latex/build/tikzz/framework_figure_style.tex paper/latex/build/tikzz/fixed_boundary_modes_a1.tex paper/latex/build/tikzz/inline_control_loop_a1.tex paper/latex/build/tikzz/taxonomy_recovery_map_a1.tex paper/latex/build/tikzz/evidence_asset_map_a1.tex
git commit -m "docs: add four standalone framework figures"
```

## Self-Review Checklist

- Spec coverage:
  - Figure 1 covers fixed optimization boundary + raw/union/llm comparison.
  - Figure 2 covers the inline control loop and recovery intervention location.
  - Figure 3 covers collapse taxonomy ↔ layered recovery mapping.
  - Figure 4 covers the evidence asset map linking compare report and single-run assets to experimental claims.

- Placeholder scan:
  - No `TODO`, `TBD`, or “implement later” steps appear in the executable tasks.
  - Every code-writing step contains exact file content.
  - Every verification step contains exact XeLaTeX commands and expected outcomes.

- Type consistency:
  - Shared palette/style names are centralized in `framework_figure_style.tex`.
  - Figure filenames use the same `_a1` suffix pattern.
  - Blue/orange/purple/green semantics stay stable across all four figures.
