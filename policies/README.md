# CrashLens Policies: Syntax, Composition, and Extension

This guide documents the YAML policy format supported by CrashLens, how matching works, available operators, actions and severities, thresholds and limits, and how to extend the system with hooks (webhooks, mutators/templates).

CrashLens evaluates each log entry against your rules using AND logic within each rule’s `match` block. When a rule matches, a violation is emitted with its configured `action` and `severity`.

## Core schema

- global: optional engine settings
- rules: list of rule objects

Example

```yaml
version: 1
global:
  # Max number of violations to record per rule before it is temporarily skipped
  max_violations_per_rule: 100

rules:
  - id: excessive_retries
    description: Cap retries to avoid storms
    match:
      metadata.fallback_attempted: true
      usage.prompt_tokens: ">= 1"
      error.code: "in:['429','5xx']"
    action: fail
    severity: high
    suggestion: Enable exponential backoff and cap retries at 2

  - id: overkill_model_for_short
    description: Avoid GPT-4 for short prompts
    match:
      input.model: "in:['gpt-4','gpt-4o','gpt-4o-mini']"
      usage.prompt_tokens: "<= 50"
      usage.completion_tokens: "<= 50"
    action: warn
    severity: medium
    suggestion: Route to gpt-4o-mini for <50+50 tokens
```

Notes
- Dot paths like `usage.prompt_tokens` access nested keys.
- All conditions in a single `match` must be true (AND).
- The engine exits early per-trace after the first rule violation for that trace to avoid noisy duplicates.

## Operators

The `match` values support:
- Equality: `==value` or plain values (`low`, `true`, `42`)
- Inequality: `!=value`
- Relational (numeric): `>`, `>=`, `<`, `<=` (engine coerces to float when possible)
- Membership: `in` and `not in` with lists, e.g. `"in:['gpt-4','gpt-4o']"`
- Regex: `regex` (uses Python re.match), e.g. `"regex:^gpt-4.*"`
- String ops: `contains`, `startswith`, `endswith`
- Lists: a YAML list means “value must be in list”

Examples

```yaml
match:
  input.model: "regex:^gpt-4.*"
  metadata.route: "contains:admin"
  metadata.team: "not in:['infra','mlops']"
  usage.prompt_tokens: "> 1000"
```

## Actions and severities

- action: one of `warn`, `fail`, `block`
- severity: one of `low`, `medium`, `high`, `critical`

These are included in violation objects and used by reporters and CI to decide pass/fail behavior.

## Thresholds and limits

Global controls:
- `global.max_violations_per_rule` caps how many times a single rule can report before being temporarily skipped for the remainder of the run.
- Early exit per trace: once any rule flags a trace, remaining rules are skipped for that trace to reduce noise and double counting.

Per-rule thresholds (pattern)
- The current engine matches per entry with AND logic. If you need “count N over window W” or “any-of”/“all-of” composites across multiple entries, see the Composite Rules section below for recommended patterns.

## Composite rules (recommended patterns)

While CrashLens’s engine evaluates single-entry AND conditions, you can achieve composite behavior in two ways:
- Pre-aggregation: Run a lightweight aggregator that annotates entries with counters (e.g., `metrics.retry_count_last_5m`) and match on those fields. You can inject these via a preprocessing step or mutator hook.
- Reporter-level grouping: Use the detailed JSON report and enforce in CI with a separate threshold step (e.g., fail if a rule group produced > X traces). See docs/ci for examples.

Proposed YAML extensions (roadmap)

```yaml
# Not yet implemented in the engine – tracked for future support
composites:
  - id: retry_storm_window
    any:
      - match: { error.code: "in:['429','5xx']" }
      - match: { metadata.fallback_attempted: true }
    threshold:
      count: ">= 3"
      window_minutes: 10
    action: fail
    severity: high
```

## Hooks and extension points

- Webhooks: Use `crashlens.utils.slack_webhook.SlackWebhookSender` to send grouped rule alerts to Slack. You can build your own webhook sender using the same contract.
- Mutators: Add a preprocessing step to enrich records (e.g., add `metrics.*` fields) before policy evaluation.
- Templates: Reporters use Jinja2 for templating in advanced setups. See docs/alerts for a Slack payload template you can adopt.

## Schema compatibility

The parser normalizes Langfuse-style logs to a stable schema (see `crashlens.parsers.langfuse`). Use dot paths like `input.model`, `usage.prompt_tokens`, `metadata.*` in your policy rules.

## Validation and troubleshooting

- Missing fields: non-existent paths evaluate as no-match.
- Type coercion: relational operators require numeric values; non-numeric triggers a non-match.
- Test policies: run locally with a small log sample; in CI, attach the JSON detailed report as an artifact for inspection.

---

For advanced policies, see examples in `examples/policies/`.
