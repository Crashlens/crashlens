import re

filepath = r'c:\Users\LawLight\Desktop\crashlens\tests\test_guard.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find self.runner.invoke(cli, [...])
pattern = r'(self\.runner\.invoke\(cli,\s*\[[\s\S]*?\]\s*)\)'

def replacer(match):
    invoke_call = match.group(1)
    # Check if this call already has env parameter
    if ', env=' in invoke_call:
        return match.group(0)  # Don't modify if env already present
    # Add env parameter
    return invoke_call + ', env={"CRASHLENS_USE_UNIFIED_ENGINE": "1", "CRASHLENS_QUIET": "1"})'

content_updated = re.sub(pattern, replacer, content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content_updated)

print('Updated test_guard.py')
