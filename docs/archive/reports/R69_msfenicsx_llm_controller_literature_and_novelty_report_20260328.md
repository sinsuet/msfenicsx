# R69 msfenicsx LLM Controller Literature and Novelty Report

Date: 2026-03-28

## Scope

This report records the literature anchor set and the novelty judgment for the next paper-facing step of the `NSGA-II` hybrid-union line:

- pure native `NSGA-II`
- union-uniform `NSGA-II`
- later union-`LLM` `NSGA-II`

The goal is not to reopen the retired `NSGA-II`-only pool branch and not to replace the multi-backbone matrix platform track.
The goal is to identify what kind of `LLM` controller design is scientifically defensible for an engineering optimization paper and what kind of design would look derivative or weak.

## Executive Conclusion

The literature does support an `LLM` policy layer for optimization, but it does not support a weak story of the form:

- add generic short-term memory
- add generic long-term memory
- call the result innovative

That alone is not a strong contribution.

For this repository, the defensible novelty is instead:

1. a fixed hybrid-union action space shared by non-`LLM` and `LLM` controller variants
2. a controller that operates only by selecting one action from that fixed registry
3. a domain-grounded state abstraction for multicase thermal feasibility and Pareto search
4. a reflective credit-assignment loop tied to expensive evaluated outcomes
5. a backbone-pluggable controller contract, with `NSGA-II` as the first implemented instance

In that framing, memory is an enabling mechanism, not the headline innovation.

The headline innovation is better described as:

- an `LLM`-guided operator hyper-heuristic on a fixed mixed native-plus-custom action space
- for expensive, constrained, multicase engineering optimization
- with matched repair, evaluation, and survival rules across the comparison ladder

## Implemented Contract Note

As of 2026-03-28, the repository now includes the first implemented `L1-union-llm-nsga2` runtime path aligned to this report's framing.

Implemented today:

- `controller=llm` spec validation with OpenAI-compatible `controller_parameters`
- an OpenAI-compatible client boundary under `llm/openai_compatible/`
- structured controller-state building from recent controller/operator traces as a compact live subset of the fuller domain-grounded state proposed in this report
- an `LLM` controller that selects only from the fixed union action registry and falls back to `random_uniform` on provider failure
- `NSGA-II` union-runtime integration with preserved repair, evaluation, and survival semantics
- sidecar artifacts for `LLM` request trace, response trace, and run metrics

Not yet validated by this implementation note:

- multi-seed comparative paper results
- full provider/model benchmarking across OpenAI-compatible ecosystems
- live-provider performance claims on the engineering benchmark
- the fuller parent/objective/violation/archive-grounded controller state described later in this report, which remains follow-up implementation work beyond the compact live subset

So the implementation status is now "code-complete for the first `L1` runtime path, experiment-complete still pending."

## Anchor Papers

The following papers are the main anchor set for this line.
They are not all evolutionary multiobjective engineering papers in the exact same form as `msfenicsx`.
Instead they provide the strongest recent evidence for where `LLM` policy layers help, where they should be constrained, and what kind of contribution statement is credible.

### 1. Large Language Models as Optimizers

- Venue: ICLR 2024
- Link: [OpenReview](https://openreview.net/forum?id=Bb4VGOWELI)
- Main relevance:
  - introduces the idea that an `LLM` can act as an optimizer by observing previous solutions and scores
  - shows the value of textualized optimization history rather than direct gradient access
- What we should take:
  - the controller should consume structured search history
  - the controller should output the next optimization decision
- What we should not copy directly:
  - free-form direct generation of the next solution vector

### 2. Large Language Models to Enhance Bayesian Optimization

- Venue: ICLR 2024
- Link: [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/84b8d9fcb4e262fcd429544697e1e720-Abstract-Conference.html)
- Main relevance:
  - treats the `LLM` as an enhancement layer rather than a total replacement of the optimization scaffold
  - highlights that `LLM` help is especially valuable when data are sparse and domain priors matter
- What we should take:
  - keep the optimizer backbone intact
  - insert the `LLM` where domain-aware selection matters most
- What we should not copy directly:
  - a surrogate-model narrative, because our expensive evaluation loop is already defined by the thermal solve and multicase report

### 3. Connecting Large Language Models with Evolutionary Algorithms Yields Powerful Prompt Optimizers

- Venue: ICLR 2024
- Link: [OpenReview](https://openreview.net/forum?id=J2SPu42l5U)
- Main relevance:
  - demonstrates that `LLM` and evolutionary mechanisms can be complementary rather than mutually exclusive
  - shows that hybridization can be stronger than either side alone when the role boundary is clear
- What we should take:
  - preserve evolutionary search identity
  - let the `LLM` guide or enrich variation-level behavior, not replace the optimizer wholesale
- What we should not copy directly:
  - prompt optimization as the task framing, because our search object is a physically repaired thermal design vector

### 4. Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model

- Venue: ICML 2024
- Link: [PMLR](https://proceedings.mlr.press/v235/liu24bs.html)
- Main relevance:
  - frames `LLM` contribution at the heuristic level rather than at the raw-solution level
  - argues that `LLM` can be useful for generating or refining decision policies under limited evaluation budgets
- What we should take:
  - the `LLM` should operate at the action-selection or heuristic layer
  - textual or symbolic policy guidance is a legitimate design target
- What we should not copy directly:
  - unconstrained heuristic generation, because our paper needs exact action-space matching across controller variants

### 5. ReEvo: Large Language Models as Hyper-Heuristics with Reflective Evolution

- Venue: NeurIPS 2024
- Link: [NeurIPS proceedings abstract](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ced59d480e07d290b6f29fc8798f195-Abstract-Conference.html)
- Main relevance:
  - the strongest direct support for a reflective `LLM` hyper-heuristic story
  - combines search with reflection over observed outcomes instead of relying on a one-shot static prompt
- What we should take:
  - use reflection over observed operator outcomes
  - treat the `LLM` as a hyper-heuristic controller
- What we should not copy directly:
  - a broad heuristic-generation claim; our controller should stay inside a fixed operator registry

### 6. FunSearch: Making New Discoveries in Mathematical Sciences Using Large Language Models

- Venue: Nature 2024
- Link: [Nature](https://www.nature.com/articles/s41586-023-06924-6)
- Main relevance:
  - separates proposal generation from authoritative external evaluation
  - uses strict evaluator feedback and diversity-preserving search structure
- What we should take:
  - keep the `LLM` outside the authority boundary
  - let repair, thermal solves, evaluation specs, and Pareto survival remain the authoritative judge
  - use compact high-value context, not uncontrolled full-history prompting
- What we should not copy directly:
  - code-synthesis framing, because our controller only needs to choose actions

## Supporting Papers For Engineering Transfer

Two additional papers are useful for framing why a domain-specific engineering instantiation can still be novel even when it borrows general mechanisms.

### Chain-of-Experts: When LLMs Meet Complex Operations Research Problems

- Venue: ICLR 2025
- Link: [OpenReview PDF](https://openreview.net/pdf?id=HobyL1B9CZ)
- Use in our story:
  - supports the idea that structured decomposition and domain-grounded intermediate reasoning matter for complex optimization settings
  - helps justify that engineering-domain adaptation is not automatically trivial

### LaMAGIC: Language-Model-based Topology Generation for Analog Integrated Circuits

- Venue: ICML 2024
- Link: [PMLR](https://proceedings.mlr.press/v235/chang24c.html)
- Use in our story:
  - supports the claim that `LLM` methods can be meaningful in engineering design when the domain representation and constraint interface are carefully specialized
  - helps justify that engineering contribution can come from a domain-specific formalization rather than from inventing an entirely new base mechanism

## Cross-Paper Synthesis

The papers above point to five stable lessons.

### 1. The `LLM` Should Usually Sit Above The Core Optimizer, Not Replace It

This is the clearest common thread across `OPRO`, the `LLM`-enhanced BO paper, EvoPrompt, and ReEvo.

For `msfenicsx`, that means:

- keep the expensive thermal evaluation loop unchanged
- keep repair unchanged
- keep survival semantics unchanged
- put the `LLM` at the proposal-control layer

### 2. The `LLM` Should Not Be Given Unlimited Freedom

The stronger papers constrain the `LLM` through:

- fixed output formats
- fixed evaluators
- externally scored outcomes
- bounded search interfaces

For `msfenicsx`, that means:

- the `LLM` should select one operator id from the fixed union registry
- the `LLM` should not emit a new eight-variable decision vector directly
- the `LLM` should not alter repair, budget, or survival

### 3. Reflection Matters More Than Generic Memory Buzzwords

The useful pattern is not "add long-term memory" in the abstract.
The useful pattern is:

- observe outcome
- summarize what worked under which regime
- reuse that information in the next decisions

That is a reflective hyper-heuristic pattern.

### 4. Domain State Representation Is A Real Design Contribution

The engineering-domain papers and the stronger optimization papers both rely on structured intermediate representations.

For `msfenicsx`, the controller state should be specialized to:

- dominant constraint regime
- near-feasible versus far-infeasible status
- multicase hot/cold pressure patterns
- recent operator effects
- current search phase

### 5. Fairness Of Comparison Is Part Of The Contribution

The strongest version of our paper is not:

- "we used an `LLM` and got better results"

The strongest version is:

- `P0` versus `P1` isolates action-space expansion
- `P1` versus `L1` isolates controller intelligence on the same action space

That fairness structure is one of the most valuable parts of the paper.

## What Would Count As Weak Novelty

The following would likely read as derivative or underwhelming:

1. taking a generic short-term plus long-term memory template from recent `LLM` agent papers and attaching it without domain specialization
2. letting the `LLM` observe raw logs and output actions without a principled state formulation
3. claiming novelty mainly from "first use of `LLM` in this exact thermal benchmark"
4. changing multiple things at once such as controller, action space, budget, and repair
5. using `NSGA-II`-specific internals so tightly that the method cannot be described as a controller framework

If the method is presented that way, reviewers can fairly say:

- the memory design is borrowed
- the contribution is mostly engineering glue
- the experiment does not isolate why the method works

## What Would Count As Stronger Novelty

The contribution becomes much stronger if we present it as a new framework with the following properties.

### 1. Fixed Hybrid-Union Action Space

The action set is held fixed across `P1` and `L1`:

- native backbone move
- shared custom engineering operators

This makes the `LLM` contribution about scheduling intelligence, not about privileged access to extra moves.

### 2. Domain-Grounded Controller State

The controller does not receive generic chat history.
It receives a structured optimization state with:

- parent summary
- feasibility status
- dominant violations
- recent action effectiveness
- archive summary
- search phase

That state abstraction is domain-specific and paper-worthy.

### 3. Reflective Credit Assignment For Expensive Engineering Search

This is where short-term and long-term memory become legitimate, but only in a specialized form.

Short-term memory:

- recent action-outcome window
- near-local regime tracking
- oscillation detection

Long-term memory:

- per-operator success statistics by regime
- feasibility transition rates
- feasible-preservation rates
- Pareto-improvement signals in feasible regions

This is not generic memory for its own sake.
It is operator credit assignment under expensive multicase engineering evaluation.

### 4. Backbone-Pluggable Controller Contract

The first implementation should remain `NSGA-II`.
However, the controller interface should be defined so that later integration with other backbones is possible without redefining the controller concept itself.

That means:

- paper experiment: `NSGA-II` only
- framework claim: backbone-pluggable controller contract
- later extension path: other backbones can provide the same native-action wrapper and state summary contract

### 5. Physics-Safe Authority Boundary

The `LLM` is not the authority.
The authority boundary stays with:

- fixed operator registry
- shared repair
- thermal solves
- evaluation spec
- optimizer survival

This is especially important for engineering credibility.

## Recommended Novelty Statement

The safest strong novelty statement is not:

- "we introduce long-term and short-term memory into evolutionary optimization"

The safer stronger statement is:

- "we introduce a backbone-pluggable `LLM`-guided operator hyper-heuristic framework for expensive multicase engineering optimization, where the `LLM` selects among a fixed hybrid-union action registry using a domain-grounded reflective state representation, while repair, evaluation, and optimizer survival remain matched across controller variants"

This wording makes clear that:

- the novelty is the framework and problem formulation
- memory is part of the controller mechanism
- the method is designed for fair matched comparisons

## Recommended Method Framing For The Paper

The method section should emphasize four layers.

### Layer 1. Search Backbone

- `NSGA-II` for the first paper-facing implementation
- later extensible to other backbones through the same controller contract

### Layer 2. Hybrid-Union Action Space

- fixed mixed action registry
- one native action plus shared custom actions

### Layer 3. Reflective `LLM` Controller

- chooses one action from the fixed registry
- uses structured state and compact memory
- does not emit raw decision vectors

### Layer 4. Authority And Evaluation Layer

- repair
- expensive thermal solves
- multicase evaluation
- native optimizer survival

This four-layer framing makes the paper cleaner than a vague "agent with memory" description.

## Memory Design Recommendation

Memory should be presented as a specialized controller mechanism, not as the main contribution headline.

Recommended memory split:

### Short-Term Memory

- last `K` controller decisions
- last `K` observed outcomes
- local regime trend such as:
  - dominant violation family
  - total-violation movement
  - feasible-entry or feasible-loss events

Purpose:

- capture local sequential dependencies
- avoid destructive oscillation
- support phase transitions

### Long-Term Memory

- per-operator outcome table aggregated over the run
- optionally stratified by regime:
  - far infeasible
  - near feasible
  - feasible refinement

Purpose:

- provide slow-moving prior beliefs
- bias selection toward actions with historically useful effects under similar regimes

### Reflection Step

- periodic summary update from recent outcomes into long-term operator statistics
- compact structured rationale retained as controller memory

Purpose:

- turn raw history into reusable control knowledge

This is much easier to defend than generic agent memory imported from unrelated settings.

## Experimental Ladder

The main paper ladder should remain:

1. pure native `NSGA-II`
2. `NSGA-II` plus the fixed hybrid-union action space under `random_uniform`
3. `NSGA-II` plus the same fixed hybrid-union action space under the reflective `LLM` controller

Recommended internal ablations:

1. `L1-lite`: structured state plus `LLM` action selection without reflection
2. `L1-stm`: add short-term memory only
3. `L1-full`: short-term plus long-term reflective controller

These ablations do not need to become headline baselines, but they are useful if reviewers ask whether the gain comes from the `LLM`, the memory, or the reflection update.

## Evidence Recommendations

The paper should avoid claiming only final-objective improvement.
For this controller story, the stronger evidence set is:

- first feasible evaluation
- feasible rate
- Pareto size
- hypervolume or another Pareto-quality metric when appropriate
- feasible-preservation rate
- dominant-violation transition patterns
- operator usage traces
- controller rationale and reflection summaries
- `LLM` failure rate, fallback rate, and API cost

This evidence makes the paper about mechanism, not only about end metrics.

## Final Judgment

Directly importing generic memory mechanisms would be a weak innovation story.

However, combining:

- fixed hybrid-union action-space control
- domain-grounded structured state
- reflective operator credit assignment
- matched engineering evaluation and repair
- backbone-pluggable controller contracts

does form a legitimate and much stronger framework contribution.

So the right answer is:

- do not sell the work as "we added memory"
- do sell the work as a new `LLM` controller framework for engineering optimization, where memory is one specialized mechanism inside a carefully matched and scientifically fair design

That framing is much more likely to survive reviewer scrutiny.

## 2026-04-01 Validation Update

The follow-up reusable controller-kernel validation has now been run under matched full-budget `11/17/23` seeds and is documented in `docs/reports/R70_msfenicsx_l1_reusable_controller_kernel_validation_20260331.md`.

That validation matters for the novelty claim in this report because it tests the approved next-step direction:

- reusable optimizer-layer policy logic
- phase-aware, evidence-aware, family-aware, and progress-aware control
- no benchmark-seed-specific or operator-name-specific permanent patches

The current evidence supports the framing in this report more strongly than the original compact `L1` note did:

- the current kernel now beats the old compact `GPT-5.4` `L1` line on average across `11/17/23` for feasible rate, time-to-first-feasible, and Pareto size
- it also beats the plain `NSGA-II` raw baseline on average across the same seeds
- it does not yet cleanly dominate `union-uniform`, because it improves average feasible rate and time-to-first-feasible but still trails slightly on mean Pareto size

So the updated scientific position is:

- the repository now has evidence for a reusable controller-kernel contribution, not only for a one-off compact live controller
- the strongest paper-facing claim is still not "the `LLM` controller wins everywhere"
- the stronger claim is "a reusable policy kernel can materially stabilize and improve the `LLM` controller line under matched optimizer contracts, while preserving a fair controller-only comparison"
