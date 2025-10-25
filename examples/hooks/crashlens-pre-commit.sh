#!/usr/bin/env bash
#
# CrashLens Pre-commit Hook
#
# Runs crashlens guard on JSONL files to enforce policy compliance
# before commits reach the repository.
#
# Usage:
#   ./crashlens-pre-commit.sh [--staged-only] [files...]
#
# Options:
#   --staged-only    Only check staged JSONL files (via git diff --cached)
#   files...         Specific JSONL files to check (passed by pre-commit)
#
# Environment Variables:
#   CRASHLENS_RULES       Path to rules.yaml (default: auto-discover)
#   CRASHLENS_SEVERITY    Minimum severity to fail (default: error)
#   CRASHLENS_OUTPUT      Output format (default: text)
#   CRASHLENS_DRY_RUN     Set to "true" to never fail (default: false)
#
# Exit Codes:
#   0 - No violations or all below severity threshold
#   1 - Violations found that meet/exceed severity threshold

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration (can be overridden by environment variables)
RULES="${CRASHLENS_RULES:-}"
SEVERITY="${CRASHLENS_SEVERITY:-error}"
OUTPUT="${CRASHLENS_OUTPUT:-text}"
DRY_RUN="${CRASHLENS_DRY_RUN:-false}"

# Parse arguments
STAGED_ONLY=false
FILES=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --staged-only)
            STAGED_ONLY=true
            shift
            ;;
        *)
            FILES+=("$1")
            shift
            ;;
    esac
done

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if crashlens is installed
check_crashlens() {
    if ! command -v crashlens &> /dev/null; then
        print_error "crashlens command not found!"
        echo "Please install crashlens: poetry install or pip install crashlens"
        exit 1
    fi
}

# Function to get staged JSONL files
get_staged_files() {
    git diff --cached --name-only --diff-filter=ACM | grep '\.jsonl$' || true
}

# Main execution
main() {
    print_info "CrashLens Guard - Pre-commit Hook"
    
    # Check if crashlens is installed
    check_crashlens
    
    # Determine which files to check
    if [ "$STAGED_ONLY" = true ]; then
        print_info "Checking staged JSONL files only..."
        mapfile -t FILES < <(get_staged_files)
    fi
    
    # Exit if no files to check
    if [ ${#FILES[@]} -eq 0 ]; then
        print_info "No JSONL files to check"
        exit 0
    fi
    
    print_info "Checking ${#FILES[@]} JSONL file(s)..."
    
    # Build crashlens command
    CMD="crashlens guard"
    
    # Add files (or use stdin if single file)
    if [ ${#FILES[@]} -eq 1 ]; then
        CMD="$CMD ${FILES[0]}"
    else
        # For multiple files, pass them all
        for file in "${FILES[@]}"; do
            CMD="$CMD $file"
        done
    fi
    
    # Add rules if specified
    if [ -n "$RULES" ]; then
        CMD="$CMD --rules $RULES"
    fi
    
    # Add options
    CMD="$CMD --severity $SEVERITY"
    CMD="$CMD --output $OUTPUT"
    CMD="$CMD --fail-on-violations"
    
    # Add dry-run flag if enabled
    if [ "$DRY_RUN" = "true" ]; then
        CMD="$CMD --dry-run"
        print_warning "Dry-run mode enabled (will not fail commit)"
    fi
    
    print_info "Running: $CMD"
    echo ""
    
    # Run crashlens guard
    if eval "$CMD"; then
        echo ""
        print_success "Guard passed: No policy violations found"
        exit 0
    else
        EXIT_CODE=$?
        echo ""
        
        if [ "$DRY_RUN" = "true" ]; then
            print_warning "Guard detected violations (dry-run mode, allowing commit)"
            exit 0
        else
            print_error "Guard failed: Policy violations detected"
            echo ""
            echo "To bypass this check temporarily:"
            echo "  git commit --no-verify"
            echo ""
            echo "To fix violations:"
            echo "  1. Review the violations above"
            echo "  2. Fix the issues in your JSONL logs"
            echo "  3. Or suppress specific rules with: crashlens guard --suppress RULE_ID"
            echo ""
            exit $EXIT_CODE
        fi
    fi
}

# Run main function
main "$@"
