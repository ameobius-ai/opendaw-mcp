#!/usr/bin/env bash
# Pre-commit hook: validate Werkstatt scripts before commit
# Install: cp scripts/pre-commit-validate.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

# Find all staged .js files in scripts/
STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep "^scripts/werkstatt_.*\.js$" || true)

if [ -z "$STAGED" ]; then
    exit 0
fi

echo "🔍 Validating Werkstatt scripts..."
cd "$(git rev-parse --show-toplevel)"

# Try venv python first, fall back to system
PYTHON="venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

for file in $STAGED; do
    result=$($PYTHON validate_scripts.py --check "$(basename "$file" .js)" 2>&1)
    if echo "$result" | grep -q "Invalid: [^0]"; then
        echo "❌ $file has malformed @param:"
        echo "$result"
        echo ""
        echo "Fix: $PYTHON autofix_params.py --check $(basename "$file" .js)"
        exit 1
    fi
done

echo "✅ All Werkstatt scripts valid"
exit 0
