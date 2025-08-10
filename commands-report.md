# CrashLens Commands Report

## Overview
CrashLens is a production-grade CLI tool for detecting token waste in GPT API logs. It analyzes Langfuse-style JSONL logs to identify inefficient usage patterns and provides cost optimization recommendations.

**Version:** 0.1.0 (Enhanced v1.2)  
**Architecture:** Production-grade with suppression engine, cost estimation, and budget enforcement

---

## Main Command Structure

### Base Command
```bash
python -m crashlens [OPTIONS] COMMAND [ARGS]...
```

**Description:** CrashLens - Detect token waste in GPT API logs

**Global Options:**
- `--version` - Show the version and exit
- `--help` - Show help message and exit

---

## Commands

### 1. `scan` - Core Detection Command

**Syntax:**
```bash
python -m crashlens scan [OPTIONS] LOG_FILE
```

**Purpose:** Scan JSONL log file for token waste patterns using production-grade detection algorithms

**Arguments:**
- `LOG_FILE` (required) - Path to the JSONL log file to analyze

**Options:**

#### Format Options (`-f`, `--format`)
- **Type:** Choice
- **Default:** `slack`
- **Values:** `slack`, `markdown`, `json`
- **Description:** Output format for detection results

**Format Details:**
- `slack` - Slack-formatted output with emojis and structured messaging
- `markdown` - Markdown-formatted output suitable for documentation
- `json` - Machine-readable JSON output for programmatic use

#### Configuration Options (`-c`, `--config`)
- **Type:** Path
- **Default:** Built-in pricing configuration
- **Description:** Path to custom pricing config file (YAML format)

**Default Configuration Path:** `crashlens/config/pricing.yaml`

---

## Detection Capabilities

### Supported Detectors (Priority Order)

1. **RetryLoopDetector** (Highest Priority)
   - Detects excessive retry patterns
   - Configurable retry thresholds and time windows
   - Suppresses lower-priority detections for same records

2. **FallbackFailureDetector** (High Priority)
   - Identifies failed fallback attempts
   - Time-window based analysis
   - Suppresses OverkillModelDetector for same records

3. **OverkillModelDetector** (Medium Priority)
   - Detects usage of overpowered models for simple tasks
   - Enhanced with cost estimation and routing suggestions
   - Provides alternative model recommendations

4. **FallbackStormDetector** (Lower Priority)
   - Identifies cascading fallback patterns
   - Configurable call thresholds and time windows
   - OSS v0.1 implementation

### Enhanced Features

#### Cost Estimation
- **Precision:** 6 decimal places (e.g., $0.000600)
- **Normalization:** All pricing normalized to 1M tokens
- **Models Supported:** GPT-4, GPT-3.5-turbo, Claude, Gemini families

#### Routing Suggestions
- Intelligent model downgrading recommendations
- Cost-benefit analysis for model alternatives
- Potential savings calculations

#### Suppression Engine
- **Production-grade:** Prevents double-counting of issues
- **Trace-level ownership:** Higher-priority detectors claim records
- **Transparent reporting:** Shows which detectors were suppressed and why

---

## Output Formats

### 1. Slack Format (Default)
```bash
python -m crashlens scan examples/demo-logs.jsonl
```
- Emoji-rich formatting
- Structured for Slack channels
- Includes severity indicators
- Suppression notes included

### 2. Markdown Format
```bash
python -m crashlens scan examples/demo-logs.jsonl -f markdown
```
- Clean markdown formatting
- Suitable for documentation
- Hierarchical structure
- Table-friendly output

### 3. JSON Format
```bash
python -m crashlens scan examples/demo-logs.jsonl -f json
```
**Sample Output:**
```json
[
  {
    "type": "overkill_model",
    "severity": "medium",
    "description": "Using gpt-4 for simple task (estimated cost: $0.000600)",
    "waste_cost": "0.000600",
    "trace_id": "trace_123",
    "suppression_notes": {
      "suppressed_detectors": [],
      "reason": null
    }
  }
]
```

---

## Configuration System

### Custom Configuration
```bash
python -m crashlens scan logs.jsonl -c /path/to/custom-config.yaml
```

### Configuration Files

#### 1. Pricing Configuration (`pricing.yaml`)
- Model pricing data (normalized to 1M tokens)
- Detection thresholds
- Cost calculation parameters
- Budget enforcement settings

#### 2. Policy Configuration (`crashlens-policy.yaml`)
- Suppression rules
- Budget policies
- Detector-specific configurations
- Priority settings

---

## Usage Examples

### Basic Scan
```bash
# Scan with default settings (Slack format)
python -m crashlens scan examples/demo-logs.jsonl
```

### Advanced Usage
```bash
# JSON output for automation
python -m crashlens scan examples/demo-logs.jsonl -f json

# Custom configuration
python -m crashlens scan examples/demo-logs.jsonl -c custom-pricing.yaml

# Markdown for documentation
python -m crashlens scan examples/demo-logs.jsonl -f markdown
```

### Poetry Integration
```bash
# Using Poetry (recommended)
poetry run python -m crashlens scan examples/demo-logs.jsonl
poetry run python -m crashlens scan examples/demo-logs.jsonl -f markdown
```

---

## Error Handling

### Common Exit Codes
- `0` - Success (detections found or no issues)
- `1` - Error (file not found, parsing error, configuration error)

### Error Messages
- File validation errors
- Configuration loading warnings
- Parser errors with trace information
- Detector execution errors

### Warnings
- Configuration fallback warnings
- Missing pricing data warnings
- Detector threshold warnings

---

## Production Features

### Budget Enforcement
- Monthly cost caps
- Threshold-based alerts
- Policy-driven controls
- Automatic suppression when budgets exceeded

### Suppression Engine
- **Principle:** Higher-priority detectors claim records first
- **Transparency:** Clear reporting of suppressed detections
- **Efficiency:** Prevents duplicate alerts for same issues
- **Flexibility:** Configurable priority hierarchy

### Cost Optimization
- Accurate cost calculations
- Model routing suggestions
- Potential savings estimation
- Budget impact analysis

---

## Command Help

### Getting Help
```bash
# Main help
python -m crashlens --help

# Command-specific help
python -m crashlens scan --help

# Version information
python -m crashlens --version
```

### Help Output
```
Usage: python -m crashlens [OPTIONS] COMMAND [ARGS]...

  CrashLens - Detect token waste in GPT API logs

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  scan  Scan JSONL log file for token waste patterns
```

---

## Technical Architecture

### Entry Points
1. **Primary:** `python -m crashlens` (via `__main__.py`)
2. **Alternative:** `crashlens.cli.cli()` (programmatic access)

### Dependencies
- **Core:** Click (CLI framework)
- **Configuration:** PyYAML
- **Data:** JSON, pathlib
- **Analysis:** Custom detector algorithms

### File Processing
- **Input:** Langfuse-style JSONL logs
- **Parser:** LangfuseParser with robust error handling
- **Output:** Multiple formats with consistent structure

---

This report covers all available commands and functionality in CrashLens v1.2 Enhanced. The tool provides production-grade token waste detection with sophisticated suppression logic, accurate cost estimation, and flexible output formatting.
