🔒 CrashLens runs 100% locally. No data leaves your system.

# CrashLens Token Waste Report

**Analysis Date:** 2025-07-28 02:20:16  

**Traces Analyzed:** 156  


## Summary

| Metric | Value |
|--------|-------|
| Total AI Spend | $1.18 |
| Total Potential Savings | $0.9157 |
| Wasted Tokens | 22,147 |
| Issues Found | 87 |
| Traces Analyzed | 156 |

## Top Expensive Traces

| Rank | Trace ID | Model | Cost |
|------|----------|-------|------|
| 1 | trace_norm_76 | gpt-4 | $0.09 |
| 2 | trace_norm_65 | gpt-4 | $0.07 |
| 3 | trace_norm_38 | gpt-4 | $0.06 |

## Cost by Model

| Model | Cost | Percentage |
|-------|------|------------|
| gpt-4 | $1.16 | 98% |
| gpt-3.5-turbo | $0.02 | 2% |


## Retry Loop (2 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0001 |
| Total Waste Tokens | 128 |

**Trace IDs**:
`trace_retry_loop_07, trace_retry_loop_10`

**Issue**: 2 traces flagged by Retry Loop

**Sample Prompts**:
1. `What is the current time in Tokyo?`
2. `What is the capital of India?`


## Fallback Storm (5 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0669 |
| Total Waste Tokens | 1,877 |

**Trace IDs**:
`trace_fallback_failure_01, trace_fallback_failure_02, trace_fallback_failure_03, trace_fallback_failure_04, trace_fallback_failure_05`

**Issue**: 5 traces flagged by Fallback Storm

**Sample Prompts**:
1. `Write a Python script to analyze sentiment from a ...`
2. `Create a function in Go to reverse a string, make ...`
3. `Summarize the key arguments in the philosophical t...`


## Fallback Failure (7 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0770 |
| Total Waste Tokens | 1,330 |

**Trace IDs**:
`trace_fallback_success_01, trace_fallback_success_02, trace_fallback_success_03, trace_fallback_success_04, trace_fallback_success_05, trace_fallback_success_06, trace_fallback_success_07`

**Issue**: 7 traces flagged by Fallback Failure


## Overkill Model (73 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.7717 |
| Total Waste Tokens | 18,812 |

**Trace IDs**:
`trace_overkill_01, trace_norm_02, trace_fallback_success_01, trace_overkill_02, trace_overkill_03, trace_norm_06, trace_overkill_04, trace_fallback_failure_01, trace_overkill_05, trace_norm_11, +58 more`

**Issue**: 73 traces flagged by Overkill Model

**Sample Prompts**:
1. `What is 2+2?`
2. `Draft a comprehensive business plan for a new e-co...`
3. `Generate a complex SQL query to find users who hav...`


## Monthly Projection

Based on current patterns, potential monthly savings: **$27.47**
