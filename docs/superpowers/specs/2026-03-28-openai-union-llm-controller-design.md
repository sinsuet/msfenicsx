# OpenAI-Compatible Union-LLM Controller Design

> Status: proposed paper-facing `L1` design for implementation after `P1-union-uniform-nsga2`.
>
> This spec specializes the broader hybrid-union paper track defined in `docs/superpowers/specs/2026-03-28-nsga2-hybrid-union-controller-design.md`.
> It does not change the active classical baseline and it does not replace the multi-backbone matrix platform track.
>
> Checked against current OpenAI official docs on 2026-03-28:
> - [Migrate to the Responses API](https://platform.openai.com/docs/guides/migrate-to-responses)
> - [Responses API reference](https://platform.openai.com/docs/api-reference/responses/retrieve)
> - [Structured model outputs](https://platform.openai.com/docs/guides/structured-outputs?lang=javascript)
> - [Prompt caching](https://platform.openai.com/docs/guides/prompt-caching)
> - [Background mode](https://platform.openai.com/docs/guides/background)
> - [Models overview](https://developers.openai.com/api/docs/models)

## 1. Goal

Define the first real `LLM` controller for the paper-facing hybrid-union line so that:

- the paper ladder remains:
  - pure native `NSGA-II`
  - `NSGA-II` plus the same hybrid-union action space under `random_uniform`
  - `NSGA-II` plus the same hybrid-union action space under `llm`
- the `LLM` is evaluated only as an action-selection strategy layer over a fixed action space
- the controller framework uses an OpenAI-compatible API surface
- the first reference implementation and compatibility baseline use the official OpenAI API
- the controller framework is model-selectable so later experiments can compare official OpenAI models and OpenAI-compatible third-party models without redefining the method
- the controller contract is backbone-pluggable even though the first implementation target remains `NSGA-II`

## 2. Hard Constraints

The following are non-negotiable for `L1`.

### 2.1 Fairness Constraints

The following must stay matched between `P1` and `L1`:

1. benchmark template
2. benchmark seed set
3. design-variable encoding
4. union action registry
5. legality repair
6. expensive evaluation loop
7. evaluation spec
8. optimizer survival semantics
9. artifact schema for optimization results

This means:

- `P1` versus `L1` differs only by controller decision making
- `L1` must not gain privileged extra operators
- `L1` must not emit raw decision vectors directly

### 2.2 Platform Constraints

- the active paper-facing classical baseline remains pure `NSGA-II`
- the first `LLM` implementation target is `NSGA-II` only
- this spec must not reopen the old removed `NSGA-II`-only pool branch
- this spec must not replace or distort the raw/union multi-backbone matrix platform story

### 2.3 API Constraints

- use an OpenAI-compatible API surface for all controller integrations
- treat the official OpenAI API as the reference semantics and first validated implementation
- use the Responses API when the target endpoint supports it
- preserve structured JSON outputs and repository-side schema validation even when a compatible provider lacks full native structured-output support
- keep model choice configurable and experiment-controlled
- support later experiments with compatible models such as Qwen, GLM, and MiniMax when they expose an OpenAI-compatible endpoint
- do not scatter provider-specific decision logic throughout optimizer core code

## 3. Contribution Framing

The paper should not sell this method as:

- "we added short-term memory"
- "we added long-term memory"
- "we used an LLM in thermal optimization"

Those framings are too weak on their own.

The defensible contribution is:

- a backbone-pluggable `LLM`-guided operator hyper-heuristic framework
- on a fixed hybrid-union action space
- for expensive constrained multicase engineering optimization
- with a domain-grounded reflective controller state
- and with matched repair, evaluation, and survival across controller variants

Memory is an internal controller mechanism, not the headline innovation.

## 4. Experiment Ladder

The paper-facing ladder remains:

### P0-Native-NSGA2

- pure native `NSGA-II`
- no custom operator controller path

### P1-Union-Uniform-NSGA2

- same `NSGA-II`
- same benchmark
- same budget
- same union action registry
- controller: `random_uniform`

### L1-Union-LLM-NSGA2

- same `NSGA-II`
- same benchmark
- same budget
- same union action registry
- controller: `llm`

Within `L1`, model comparison is a method-internal study rather than a new baseline ladder.

Examples:

- `L1-gpt-4o-mini`
- `L1-gpt-4o`
- `L1-gpt-5-mini`
- `L1-gpt-5.4`
- `L1-qwen-compatible`
- `L1-glm-compatible`
- `L1-minimax-compatible`

If slower pro-tier models are studied later, they must be reported as model variants inside `L1`, not as new methods.

## 5. Method Overview

The proposed `L1` controller has four layers.

### 5.1 Backbone Layer

- the search backbone remains `NSGA-II` in the first implementation
- parent selection and survival remain native `NSGA-II`
- the controller only intervenes at proposal-time action selection

### 5.2 Hybrid-Union Action Layer

The action registry remains fixed:

1. `native_sbx_pm`
2. `sbx_pm_global`
3. `local_refine`
4. `hot_pair_to_sink`
5. `hot_pair_separate`
6. `battery_to_warm_zone`
7. `radiator_align_hot_pair`
8. `radiator_expand`
9. `radiator_contract`

The `LLM` may select only one operator id from this registry for each proposal decision.

### 5.3 Reflective Controller Layer

The `LLM` receives a structured optimization-state summary and returns:

- one selected operator id
- one compact phase label
- one compact rationale

The controller uses:

- short-term memory:
  - recent decision/outcome window
  - recent dominant-violation trends
  - recent oscillation or regression flags
- long-term memory:
  - per-operator success statistics by regime
  - feasible-entry and feasible-preservation frequencies
  - regime-conditioned improvement summaries
- periodic reflection:
  - summarize what actions helped or harmed under the current regime
  - update the long-term controller memory in compact structured form

### 5.4 Authority Layer

The `LLM` is never the authority.
The authority remains:

- fixed operator registry
- shared repair
- expensive thermal solves
- multicase evaluation
- native optimizer survival

This keeps the method engineering-safe and scientifically fair.

## 6. OpenAI-Compatible Integration Design

## 6.1 API Choice

Per OpenAI's current docs, the Responses API is recommended for new projects and supports structured outputs, stateful interactions, and tool extensions.
For this controller, the official OpenAI Responses API should be treated as the reference implementation and semantic baseline.

However, the framework must also allow later experiments with models served through OpenAI-compatible endpoints, including examples such as:

- Qwen-family hosted endpoints with OpenAI-compatible request formats
- GLM-family hosted endpoints with OpenAI-compatible request formats
- MiniMax hosted endpoints with OpenAI-compatible request formats

Implication:

- the first implementation should not be built on a provider-specific custom SDK
- the repository should define one controller client contract and attach provider capability profiles behind it
- do not let provider differences change the optimization method definition

Recommended capability profiles:

1. `responses_native`
   - official OpenAI Responses API semantics
   - native structured outputs when supported
2. `chat_compatible_json`
   - OpenAI-compatible chat or completions transport
   - repository-enforced JSON/schema validation

Method rule:

- provider capability changes transport details
- provider capability must not change the fixed controller state schema, action registry, or fallback logic

## 6.2 Structured Outputs

Use structured outputs with JSON schema for every controller decision.
Per OpenAI's current structured-output docs, strict schema adherence is supported for compatible models and should be preferred when the schema fits the supported subset.

Design rule:

- the controller request must ask for structured JSON output
- the response must be validated twice:
  - API/schema validation
  - repository-side semantic validation

Repository-side semantic validation still must confirm:

- `selected_operator_id` belongs to the current operator registry
- `phase_label` is one of the repository-approved labels
- the response belongs to the requested decision batch

Compatibility rule:

- if a compatible provider does not support strict server-side JSON schema enforcement, the repository must still enforce the same output schema after response receipt
- those runs must log the provider capability profile so model-comparison tables remain interpretable

## 6.3 Stateless By Default

The Responses API supports conversation state, but the first implementation should be stateless by default.

Rationale:

- easier replay and debugging
- easier model-to-model fairness
- easier prompt hashing and caching
- easier artifact reproducibility
- no hidden server-side conversation drift

Therefore:

- keep controller memory in repository artifacts, not in remote conversation state
- send the needed compact memory summary explicitly in each request
- set the prompt so the static instruction prefix appears first and dynamic state later

This is an inference from OpenAI prompt-caching guidance and our reproducibility requirements.

## 6.4 Prompt Caching

OpenAI prompt caching currently works automatically for sufficiently long shared prefixes and rewards placing static prompt content first.
The controller design should take advantage of this.

Design rule:

- keep the static controller instructions, schema description, and operator descriptions at the beginning of the prompt
- place dynamic run state and per-decision summaries at the end
- use consistent prompt templates and versions across experiments
- log cached-token usage so cost and latency analysis can include cache behavior

## 6.5 Background Mode

OpenAI background mode exists for longer-running responses.
The default `L1` implementation should remain synchronous.

However:

- background mode may be enabled as an opt-in execution policy for slower models if timeout or latency becomes a practical blocker
- if background mode is used, the run artifacts must record that fact because it changes operational behavior and retention assumptions

Initial default:

- `background = false`
- `stream = false`
- `store = false` when compatible with the request mode

Background mode should remain a runtime option, not a method-defining feature.

## 7. Model-Selectable Framework

The method must be model-selectable while staying inside an OpenAI-compatible API ecosystem.

This means:

- the framework prompt, state schema, memory schema, output schema, fallback rules, and trace contract remain fixed
- the chosen `(provider, capability_profile, model_id)` tuple is an experiment variable
- the reported model id should be snapshot-pinned whenever stable reproducibility is required
- official OpenAI models and compatible third-party models should be compared inside the same framework only when their runtime capability profile is clearly recorded

As of 2026-03-28, OpenAI's models guide recommends:

- `gpt-5.4` as the flagship general starting point
- smaller variants such as `gpt-5-mini` for lower latency and cost

Also useful for controller studies:

- `gpt-4o-mini` as a cheap structured-output baseline
- `gpt-4o` as a strong non-o-series baseline

Future compatible-endpoint examples may include:

- Qwen variants
- GLM variants
- MiniMax variants

These should be reported as:

- same `L1` framework
- different model provider or serving stack
- same controller-state and action-selection contract

The method claim should therefore be:

- one `L1` framework
- multiple official OpenAI and OpenAI-compatible models compared inside that framework

Not:

- one different method per model

## 7.1 Performance Profiles

For experimental performance, the framework should support higher-capability inference settings such as:

- stronger reasoning or "thinking" modes when the target model exposes them
- larger `max_output_tokens` budgets
- higher-latency but higher-quality runtime profiles when available

For official OpenAI reasoning models, current docs indicate:

- `reasoning.effort` is a supported knob for reasoning models
- higher effort trades more latency and token usage for stronger reasoning
- `max_output_tokens` is an upper bound that covers both visible output and reasoning tokens
- OpenAI recommends starting with a generous token budget when experimenting with reasoning workflows

For this repository, these settings must be treated as controlled runtime profiles, for example:

- `fast`
- `balanced`
- `high_reasoning`

Each profile should pin at least:

- provider
- capability profile
- model id
- reasoning-effort setting when supported
- `max_output_tokens`
- timeout policy
- retry policy

Important fairness rule:

- changing reasoning effort or token budget changes the runtime profile, not the method definition
- comparisons across models should first use matched performance profiles
- any extra tuning study with more aggressive reasoning settings should be reported as a separate profile analysis, not silently folded into the main headline comparison

Recommended first-paper strategy:

- main comparison: one matched `balanced` profile across all tested models
- secondary analysis: one `high_reasoning` profile for the strongest candidate models

This keeps the headline experiment fair while still allowing us to test whether stronger inference settings materially improve controller quality.

## 7.2 Thinking And Token Controls

The controller framework should expose the following runtime knobs when the target endpoint supports them:

- reasoning effort or equivalent "thinking" control
- `max_output_tokens`
- temperature
- top-p when needed, though the default should remain conservative for structured outputs
- service tier or analogous latency-quality controls when available

Recommended defaults for structured controller decisions:

- low temperature
- structured output mode on
- sufficient token budget to avoid truncating reasoning or the final JSON output

Repository rule:

- all runtime knobs used in a run must be logged in `llm_metrics.json` and request traces
- profile names must be versioned so later experiments are reproducible

## 8. Backbone-Pluggable Contract

Although the first paper-facing implementation is `NSGA-II`, the controller contract should not be named or typed as `NSGA2OnlyController`.

The controller contract should be organized around:

- `family`
- `backbone`
- `candidate_operator_ids`
- `controller_state_payload`

The first implementation only needs one real state builder:

- genetic family
- `nsga2`
- union mode

But the contract should allow later additions where other backbones provide:

- their native operator id
- their parent-selection context
- their state-summary adapter

without redefining the controller semantics itself.

## 9. Controller State Design

The current repository `ControllerState` is too thin for `L1`.
The `LLM` controller needs a richer state payload.

The proposed state should be split into six blocks.

### 9.1 Run Block

- run id
- generation index
- decision index
- expensive evaluations used
- expensive evaluations remaining
- current feasible rate
- first feasible found or not
- current search phase

### 9.2 Parent Block

- parent indices
- parent decision vectors
- repaired parent summary if available
- parent feasibility status
- parent total violation
- parent dominant active violation
- parent objective summary when feasible

### 9.3 Archive Block

- best near-feasible summary
- best feasible summary
- selected Pareto representatives
- current front diversity summary

### 9.4 Operator-Statistics Block

For each operator id:

- usage count
- recent usage count
- feasible-entry count
- feasible-preservation count
- average violation delta
- average objective-improvement summary in feasible region
- last observed dominant-regime tags where it helped

### 9.5 Reflection-Memory Block

- recent reflection summary
- current regime hypothesis
- recent harmful action patterns
- recent helpful action patterns

### 9.6 Domain-Regime Block

This is one of the main domain contributions.
The state must explicitly characterize the local engineering regime, for example:

- far infeasible
- near feasible
- feasible refinement
- hot-side dominant
- cold-side dominant
- geometry-dominant
- mixed-regime

The exact regime taxonomy should be derived from actual evaluation outputs and active constraint names, not from generic agent labels.

## 10. Decision Granularity And Cost Control

Calling the OpenAI API once per proposal decision is the simplest design, but it may be too expensive or slow for broad model studies.

Therefore the controller design should support two execution modes.

### 10.1 Mode A: Single-Decision Calls

Use one API call per proposal decision.

Pros:

- simplest to implement
- easiest to debug
- cleanest trace semantics

Cons:

- higher token and latency overhead

### 10.2 Mode B: Generation-Level Batched Decisions

Use one API call to select actions for a batch of proposal decisions from the same generation.

Pros:

- lower per-decision overhead
- better prompt-cache leverage
- more practical for multi-model comparison campaigns

Cons:

- larger prompts
- more complex response validation

Recommendation:

- implement the controller framework so both modes are possible
- start with single-decision correctness
- move to generation-level batching for scale if the first correctness path is stable

This implies the controller contract should evolve from a scalar-only selector toward an interface that can support batched decision requests.

## 11. Output Schema

The controller response should use a strict structured schema close to:

```json
{
  "decision_batch": [
    {
      "decision_index": 17,
      "selected_operator_id": "battery_to_warm_zone",
      "phase_label": "repair",
      "confidence": 0.78,
      "brief_rationale": "Cold-side battery violation dominates and this action has helped similar near-feasible states."
    }
  ],
  "reflection_update": {
    "regime_label": "cold_dominant_near_feasible",
    "helpful_patterns": [
      "battery_to_warm_zone after local_refine preserved feasibility pressure"
    ],
    "harmful_patterns": [
      "radiator_contract often reopens cold-side violation in this regime"
    ]
  }
}
```

Repository rules:

- `decision_index` must match a requested decision
- `selected_operator_id` must be in the current candidate registry
- `phase_label` must be one of the repository-approved labels
- `confidence` is optional analysis metadata, not a hard method dependency
- `brief_rationale` is for traceability and later mechanism analysis
- `reflection_update` may be optional in the first minimal implementation

## 12. Reflection And Credit Assignment

The `LLM` controller must not be stateless in the final method framing.
However, its memory should be grounded in optimization outcomes rather than in generic conversational history.

### 12.1 Short-Term Credit

Track recent transitions such as:

- infeasible to feasible
- feasible to infeasible
- total-violation decrease
- dominant-violation switch
- feasible-region Pareto improvement

### 12.2 Long-Term Credit

Maintain aggregated per-operator statistics by regime such as:

- success when hot-side constraints dominate
- success when cold-side constraints dominate
- success near feasibility
- success in feasible refinement

### 12.3 Reflection Trigger

Reflection should happen on a controlled schedule, for example:

- every generation
- every `N` decisions
- on regime change
- on first feasible discovery

Recommendation:

- start with generation-level reflection
- keep the reflection output compact and structured

## 13. Fallback Policy

The first implementation must treat API failures and invalid outputs as expected operational cases.

Fallback order:

1. retry with the same model and same structured schema when the failure is transient
2. if the response is syntactically valid but semantically invalid, retry once with an explicit correction instruction
3. if still invalid or rate-limited beyond policy, fall back to deterministic repository logic

Recommended deterministic fallback:

- first choice: a lightweight repository-side heuristic using current regime and operator statistics
- second choice: `random_uniform`

Every fallback event must be logged in artifacts with:

- reason
- provider
- model id
- capability profile
- request id if available
- retry count
- final fallback operator

## 14. Artifact And Trace Design

In addition to existing controller and operator traces, `L1` should write separate `LLM` sidecars.

Recommended sidecars:

- `llm_request_trace.jsonl`
- `llm_response_trace.jsonl`
- `llm_reflection_trace.jsonl`
- `llm_metrics.json`

These should record:

- provider
- model id
- capability profile
- performance profile
- reasoning effort if used
- `max_output_tokens`
- prompt template version
- state schema version
- output schema version
- latency
- usage tokens
- cached tokens when available
- retries
- fallback events
- selected operator ids
- compact rationale text
- reflection summaries

The optimization result contract itself should remain clean and not embed raw prompt payloads.

## 15. Security And Data Boundary

Because this is an engineering workflow:

- do not send unnecessary repository text or large raw artifacts to the model
- do send compact structured optimization state only
- keep secrets in environment variables such as `OPENAI_API_KEY`
- keep provider configuration outside committed source secrets

If background mode or webhooks are later used, their secrets and endpoint details must remain external configuration.

## 16. Reporting Rules

The paper and reports should separate:

- optimization performance
- controller mechanism behavior
- OpenAI model operating cost

At minimum, `L1` reporting should include:

- seed set
- expensive-evaluation budget
- first feasible evaluation
- feasible rate
- Pareto size
- hypervolume or another Pareto quality metric when appropriate
- operator usage distribution
- dominant-violation transition analysis
- model latency
- API token cost
- cache hit behavior if available
- fallback frequency
- runtime performance profile
- reasoning-effort setting when used
- configured and effective token budget

## 17. Non-Goals

This spec does not require, in the first implementation wave:

- direct `LLM` emission of decision vectors
- bespoke deeply customized provider-specific controller logic
- immediate support for other backbones at runtime
- reinforcement fine-tuning before a strong zero-shot or in-context baseline exists
- replacing the multi-backbone matrix platform story

## 18. Acceptance Criteria

This design is acceptable only if:

1. the first implementation stays within the existing `P0 -> P1 -> L1` paper ladder
2. `L1` differs from `P1` only by controller decision making
3. the first reference implementation is validated on the official OpenAI API
4. the controller output is structured and schema-validated across official and compatible endpoints
5. the controller framework is model-selectable across official OpenAI and OpenAI-compatible models
6. the method is presented as one framework with model comparison inside it
7. runtime performance tuning such as stronger thinking modes or larger token budgets is recorded as a profile-level experiment factor rather than silently changing the method
8. the controller state is domain-grounded rather than generic conversational memory
9. reflection and memory are described as internal controller mechanisms, not as the headline novelty
10. the contract remains backbone-pluggable even though `NSGA-II` is the first implemented backbone
11. the run artifacts expose enough trace information to analyze why the `LLM` chose each operator and what happened afterward

## 19. Recommended Next Step

The next implementation plan should focus on five concrete work packages:

1. extend the controller-state contract to support the structured `L1` state payload
2. add an OpenAI-only `LLM` controller implementation on the Responses API with structured outputs
3. implement reflection memory and repository-side fallback logic
4. add `LLM`-specific artifact sidecars and verification tests
5. run an initial `NSGA-II`-only model study inside the fixed `L1` framework
