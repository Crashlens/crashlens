from crashlens.policy.engine import PolicyEngine
from crashlens.parsers.langfuse import LangfuseParser

# Load and analyze logs
parser = LangfuseParser()
traces_by_id = parser.parse_file("cold-dev-test.jsonl")

# Flatten all records into a list
traces = [record for records in traces_by_id.values() for record in records]

# Apply policies
engine = PolicyEngine(r"policies\langfuse\ci-sample.yaml")
violations, skipped = engine.evaluate_logs(traces)

print(f"Found {len(violations)} violations")