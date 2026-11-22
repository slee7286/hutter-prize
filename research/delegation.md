# Where another model call is worth its cost

**Project decision:** use scripts first; use one inexpensive reader for bounded evidence extraction; let the premium parent decide consequential questions. A second premium researcher is an exception, not the default. This is about preserving research quality per token, not merely reducing elapsed time.

## Evidence behind the decision (22 November 2026)

- **Local baseline:** the six completed child sessions of the two original three-worker waves used the premium `gpt-6.2-astra` model. Their session counters sum to 135 API calls, 909,207 input tokens, 47,249 output tokens and 4,896,128 cache-read tokens. These are separate runtime counters, not additive billable tokens. This excludes the parent and is not a dollar invoice. The earlier [partial-session receipt](site/usage-note.txt) overlaps this population; don't add the two. The workers found real artifacts, so the lesson is not “delegation failed.” It is that splitting by package did not make any worker cheaper.
- [Anthropic’s engineering report](https://www.anthropic.com/engineering/multi-agent-research-system) reports roughly 15× chat token use for its multi-agent research system **in its own data**. It found delegation useful for breadth, provided the lead assigns clear objectives, tools, boundaries and outputs. This is not a 15× estimate for this repo. Separate independent archive-provenance questions, not successive steps of one decode.
- [Hermes delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation) gives a child its own context and returns a summary; it inherits the main model unless delegation is configured otherwise. An instruction to “think cheaply” is not model routing. Do not change the user's global profile. A project-scoped worker invocation must explicitly name the model; if unavailable, use deterministic tools or report the blocker, not a silent upgrade.
- [OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection) recommends testing fit on the actual workload, reserving stronger reasoning for demanding analysis. Its [prompt-caching guide](https://developers.openai.com/api/docs/guides/prompt-caching) distinguishes reusable prefixes from variable suffixes. Keep instructions short and stable; send just the changed evidence. A cache read is neither a free token nor a guarantee of future hits.

## Routing decisions for this repository

| Work | Default | Required evidence |
|---|---|---|
| Fetch a known URL, hash a file, compare output, compute a score, check job state | Shell/Python; **no child** | Receipt or exact command/output |
| Extract a claim or locate a caveat in an already retrieved passage | Bounded economy reader if deterministic extraction isn't enough | File or URL locator, exact short quote and uncertainty |
| Reconcile mismatched award/public builds, interpret a disputed rule, choose an ablation before a multi-day run | Premium parent uses the verified evidence packet | Alternatives, falsifying check and effect on the next decision |
| Truly independent high-stakes challenge to the parent's reasoning | One premium reviewer only if a specific unresolved question and cost of error are written down | New evidence or a test that could reverse the conclusion; disagreement alone isn't evidence |

One owner per question; do not assign the same evidence search to several models for a vote. Record what is already known, one narrow question, the exclusion boundary and a stop condition. Store logs locally, send locators/snippets, return a short evidence delta. If a worker fails, check its artifacts before retrying; if it adds no evidence, stop or change the method. Use isolated deterministic processes for long replays; no agent polling. Only the integrator verifies, commits and pushes. A child cannot declare a prize run verified: require the actual full-corpus receipt. Never sacrifice this check to lower spend.

Measure verified decisions and corrections, not number of agents or paragraphs. For a policy change, use the same frozen evidence packets across routes, blind the reviewer to model identity, and grade source fidelity, distinction between original and variant, and the proposed next check. Track parent review/rework as well as child usage. Prefer the cheaper route only if it meets the evidence standard; otherwise escalate **the disputed point**, not the entire history. No savings percentage is established without a matched quality comparison.
