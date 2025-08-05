#!/usr/bin/env python3
"""
Direct test of CrashLens init templates (no imports)
"""

import yaml

# Copy the template definitions directly for testing
TEMPLATE_YAMLS = {
    "retry-limit": """# CrashLens Policy Template: Retry Limit Control
# Prevents excessive retry patterns that can cause cost explosions

rules:
  - id: retry_limit_exceeded
    description: "Limit the number of retries in a request trace"
    match:
      retry_count: ">2"
    action: warn
    severity: medium
    suggestion: "Implement exponential backoff and circuit breaker patterns"
    requires_license: false

global:
  max_violations_per_rule: 50
  enable_cost_estimation: true

cost_thresholds:
  warning_threshold: 0.05
  critical_threshold: 0.20
""",
    
    "basic-safety": """# CrashLens Policy Template: Basic Safety & Cost Controls
# Essential safety rules for production AI usage

rules:
  - id: expensive_model_simple_task
    description: "Warn if GPT-4 is used for short prompts (simple tasks)"
    match:
      input.model: ["gpt-4", "gpt-4-turbo", "claude-3-opus"]
      usage.prompt_tokens: "<50"
    action: warn
    severity: medium
    suggestion: "Consider using gpt-3.5-turbo or gpt-4o-mini for simple tasks"
    requires_license: false
    
  - id: unauthorized_model_usage
    description: "Block usage of non-approved models"
    match:
      input.model: "not in:['gpt-3.5-turbo', 'gpt-4', 'gpt-4o-mini', 'claude-3-haiku']"
    action: fail
    severity: critical
    suggestion: "Use only approved models from the organizational whitelist"
    requires_license: false

global:
  max_violations_per_rule: 100
  enable_cost_estimation: true
""",
    
    "cost-cap": """# CrashLens Policy Template: Cost Cap & Budget Controls
# Strict cost controls to prevent budget overruns

rules:
  - id: high_cost_request_block
    description: "Block completions costing more than threshold"
    match:
      cost: ">0.10"
    action: fail
    severity: critical
    suggestion: "Request exceeds cost limit - optimize prompt or use cheaper model"
    requires_license: false

global:
  max_violations_per_rule: 25  # Strict enforcement
  enable_cost_estimation: true

cost_thresholds:
  warning_threshold: 0.05
  critical_threshold: 0.10
  daily_budget: 25.00
  monthly_budget: 500.00
"""
}

print("🧪 Testing CrashLens init templates")
print("=" * 40)

# Test YAML validity
for template_name, content in TEMPLATE_YAMLS.items():
    try:
        parsed = yaml.safe_load(content)
        rules_count = len(parsed.get('rules', []))
        has_global = 'global' in parsed
        print(f"✅ {template_name}: {rules_count} rules, global config: {has_global}")
    except Exception as e:
        print(f"❌ {template_name}: YAML error - {e}")

# Test template content
print(f"\n📄 Sample template preview (basic-safety):")
lines = TEMPLATE_YAMLS["basic-safety"].split('\n')[:15]
for line in lines:
    print(f"   {line}")

print(f"\n🎉 Template validation complete!")
print(f"📊 {len(TEMPLATE_YAMLS)} templates available")
print(f"\n💡 CLI usage examples:")
print(f"   crashlens init --template basic-safety")
print(f"   crashlens init --template cost-cap --output budget.yaml")
print(f"   crashlens list-templates --verbose")
