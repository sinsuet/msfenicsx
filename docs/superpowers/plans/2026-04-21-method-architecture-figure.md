# Method Architecture Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reference-styled TikZ architecture figure as a test-only standalone artifact under `paper/latex/build/tikzz/`, compile it with the existing TeX environment, and keep all source/build outputs confined to that directory.

**Architecture:** Build the figure as a standalone TikZ document so layout and compilation stay isolated from the manuscript body. This execution path does not modify or include anything from `paper/latex/sections/zh/04_method.tex`; it only produces a test-only compiled figure under `paper/latex/build/tikzz/`.

**Tech Stack:** XeLaTeX, TikZ/PGF, standalone class, existing TeX environment, direct compilation-based verification.

**Spec:** [docs/superpowers/specs/2026-04-21-method-architecture-figure-design.md](../specs/2026-04-21-method-architecture-figure-design.md)

---

### Task 1: Create the standalone TikZ figure skeleton

**Files:**
- Create: `paper/latex/build/tikzz/method_architecture_a1.tex`
- Verify: `paper/latex/build/tikzz/method_architecture_a1.pdf`

- [ ] **Step 1: Write the initial standalone figure source**

```tex
\documentclass[tikz,border=6pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc,backgrounds}

\begin{document}
\begin{tikzpicture}
\node {Method architecture A1 draft};
\end{tikzpicture}
\end{document}
```

- [ ] **Step 2: Run XeLaTeX to verify the initial figure compiles before styling**

Run: `xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/method_architecture_a1.tex`

Expected: PASS and `paper/latex/build/tikzz/method_architecture_a1.pdf` exists.

- [ ] **Step 3: Replace the initial draft with the real A1 TikZ layout**

```tex
\documentclass[tikz,border=8pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit,calc,backgrounds}

\definecolor{panelblueborder}{HTML}{3A86C8}
\definecolor{panelbluefill}{HTML}{EAF3FB}
\definecolor{panelorangeborder}{HTML}{E67E22}
\definecolor{panelorangefill}{HTML}{FDF1E3}
\definecolor{feedbackpurple}{HTML}{8E44AD}
\definecolor{routegray}{HTML}{333333}
\definecolor{lightgraydash}{HTML}{BDBDBD}

\tikzset{
  panel/.style={rounded corners=6pt, very thick, inner sep=14pt},
  mainpanel/.style={panel, draw=panelblueborder, fill=panelbluefill},
  sidepanel/.style={panel, draw=panelorangeborder, fill=panelorangefill},
  card/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=3.4cm, minimum height=1.15cm, align=center, line width=0.8pt},
  smallcard/.style={draw=routegray, rounded corners=4pt, fill=white, minimum width=2.7cm, minimum height=1.0cm, align=center, line width=0.8pt},
  ctrlraw/.style={smallcard},
  ctrlunion/.style={smallcard, draw=panelorangeborder},
  ctrlllm/.style={smallcard, draw=feedbackpurple, dashed},
  flow/.style={-Latex, line width=0.95pt, draw=routegray},
  accentflow/.style={-Latex, line width=1.0pt, draw=panelblueborder},
  feedback/.style={-Latex, line width=1.0pt, draw=feedbackpurple, dashed},
  note/.style={align=left, text width=4.8cm, font=\small},
  titlelabel/.style={font=\bfseries\large},
  sectionlabel/.style={font=\bfseries}
}

\begin{document}
\begin{tikzpicture}[node distance=0.55cm and 0.8cm]
  \node[titlelabel, text=panelblueborder, anchor=west] (lefttitle) at (0,5.1) {Shared Optimization Backbone};

  \node[card, minimum width=5.2cm, minimum height=1.35cm, below=0.45cm of lefttitle.west, anchor=west] (repr) {
    \textbf{Representation Layer}\\
    15 component $x/y$ variables + sink boundary variables
  };

  \node[card, minimum width=5.2cm, minimum height=1.35cm, below=0.55cm of repr] (ops) {
    \textbf{Shared Operator Layer}\\
    semantic shared operator registry + candidate action families
  };

  \node[card, minimum width=5.2cm, minimum height=1.45cm, below=0.55cm of ops] (eval) {
    \textbf{Shared Repair / Evaluation Layer}\\
    geometry repair $\rightarrow$ cheap constraints $\rightarrow$ expensive PDE evaluation
  };

  \node[ctrlraw, below left=1.15cm and 0.15cm of eval] (raw) {
    \textbf{raw}\\ baseline evolutionary\\ scheduling
  };
  \node[ctrlunion, below=1.15cm of eval] (union) {
    \textbf{union}\\ shared-registry\\ non-LLM scheduling
  };
  \node[ctrlllm, below right=1.15cm and 0.15cm of eval] (llm) {
    \textbf{llm}\\ state-guided online\\ semantic scheduling
  };

  \node[font=\small, text=routegray, above=0.2cm of raw.north west, anchor=south west] (ctrlcaption) {Controller layer only changes scheduling policy};

  \begin{scope}[on background layer]
    \node[mainpanel, fit=(repr)(ops)(eval)(raw)(union)(llm)(ctrlcaption), inner xsep=16pt, inner ysep=15pt] (mainpanelbox) {};
  \end{scope}

  \node[titlelabel, text=panelorangeborder, anchor=west] (righttitle) at ($(mainpanelbox.east)+(2.0,4.2)$) {Fair-Comparison Constraints};
  \node[sidepanel, anchor=north west, minimum width=5.9cm, minimum height=4.6cm] (sidebox) at ($(righttitle.south west)+(0,-0.35)$) {};
  \node[note, anchor=north west] at ($(sidebox.north west)+(0.38,-0.45)$) {
    \textbf{Fixed across modes}\\[2pt]
    $\bullet$ same representation\\
    $\bullet$ same operator pool\\
    $\bullet$ same repair / cheap filtering / evaluation\\
    $\bullet$ same optimization budget\\[6pt]
    \textbf{Only controller differs}\\
    decision policy for action scheduling
  };

  \draw[flow] (repr) -- (ops);
  \draw[flow] (ops) -- (eval);
  \draw[accentflow] (raw.north) |- ($(ops.south west)!0.20!(ops.south east)$);
  \draw[accentflow] (union.north) -- (ops.south);
  \draw[accentflow] (llm.north) |- ($(ops.south west)!0.80!(ops.south east)$);
  \draw[feedback] (eval.east) .. controls +(1.45,0.15) and +(1.2,-1.15) .. ($(llm.east)+(0.1,0.12)$);
  \draw[feedback] (eval.east) .. controls +(1.25,0.7) and +(1.55,0.5) .. ($(union.east)+(0.12,0.35)$);
  \draw[feedback] (eval.west) .. controls +(-1.25,0.55) and +(-1.25,0.45) .. ($(raw.west)+(-0.12,0.3)$);

  \node[font=\small, text=feedbackpurple, anchor=west] at ($(mainpanelbox.north west)+(0.35,0.35)$) {compressed state / progress signals};
  \draw[lightgraydash, dashed] ($(mainpanelbox.north east)+(0.35,-0.35)$) -- ($(sidebox.north west)+(-0.2,-0.35)$);
\end{tikzpicture}
\end{document}
```

- [ ] **Step 4: Re-run XeLaTeX to verify the real figure compiles**

Run: `xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/method_architecture_a1.tex`

Expected: PASS and a readable `paper/latex/build/tikzz/method_architecture_a1.pdf`.

### Task 2: Compile and verify the standalone figure only

**Files:**
- Verify: `paper/latex/build/tikzz/method_architecture_a1.pdf`

- [ ] **Step 1: Compile the standalone figure with the existing TeX environment**

Run: `xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/method_architecture_a1.tex`

Expected: PASS and a readable `paper/latex/build/tikzz/method_architecture_a1.pdf`.

- [ ] **Step 2: Confirm all source/build outputs remain under the TikZ test directory**

Check for these artifacts:

```text
paper/latex/build/tikzz/method_architecture_a1.tex
paper/latex/build/tikzz/method_architecture_a1.pdf
paper/latex/build/tikzz/method_architecture_a1.log
paper/latex/build/tikzz/method_architecture_a1.aux
```

Expected: all generated artifacts stay under `paper/latex/build/tikzz/`.

### Task 3: Polish the TikZ layout and verify artifacts

**Files:**
- Modify: `paper/latex/build/tikzz/method_architecture_a1.tex`
- Verify: `paper/latex/build/tikzz/method_architecture_a1.pdf`

- [ ] **Step 1: Check the compiled figure for style drift and crowding**

Review these visual requirements against the compiled PDF:

```text
- soft blue left panel and soft orange right panel
- rounded white internal cards
- dark primary flow lines
- restrained accent colors only
- right panel reads as explanatory support, not a second main figure
- raw/union/llm look like controller variants, not different pipelines
```

- [ ] **Step 2: If needed, make the minimal TikZ adjustments for spacing or routing**

Allowed edits are limited to values like these inside `paper/latex/build/tikzz/method_architecture_a1.tex`:

```tex
node distance=0.55cm and 0.8cm
minimum width=5.2cm
minimum height=1.35cm
controls +(1.45,0.15) and +(1.2,-1.15)
inner xsep=16pt
inner ysep=15pt
```

Do not change semantics while polishing layout.

- [ ] **Step 3: Recompile the standalone figure after any adjustment**

Run: `xelatex -interaction=nonstopmode -halt-on-error -output-directory paper/latex/build/tikzz paper/latex/build/tikzz/method_architecture_a1.tex`

Expected: PASS and updated `paper/latex/build/tikzz/method_architecture_a1.pdf`.
