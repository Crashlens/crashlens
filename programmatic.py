from crashlens.policy.engine import PolicyEngine
from crashlens.parsers.langfuse import LangfuseParser

# Load and analyze logs
parser = LangfuseParser()
traces = parser.parse_file("cold-dev-test.jsonl")

# Apply policies
engine = PolicyEngine(r"policies\langfuse\ci-sample.yaml")
violations, skipped = engine.evaluate_logs(traces)

print(f"Found {len(violations)} violations")