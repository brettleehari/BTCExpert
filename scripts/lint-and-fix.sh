#!/bin/bash
# CIAL Unified Lint & Fix Script
# This script aligns local development, pre-commit hooks, and CI pipeline.

set -e

# Configuration
WORKING_DIR="cial"
LINE_LENGTH=100

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting CIAL Unified Lint & Fix Suite${NC}"

# Ensure we are in the root directory
if [ ! -d "$WORKING_DIR" ]; then
    echo -e "${RED}Error: Must be run from the repository root.${NC}"
    exit 1
fi

# 1. Format with Black
echo -e "${BLUE}Step 1: Formatting with Black...${NC}"
black --line-length=$LINE_LENGTH --exclude "venv/|\.venv/|__pycache__/|\.pytest_cache/|\.ruff_cache/|htmlcov/|\.coverage" "$WORKING_DIR"

# 2. Sort imports with isort
echo -e "${BLUE}Step 2: Sorting imports with isort...${NC}"
isort --profile=black --line-length=$LINE_LENGTH --skip "$WORKING_DIR/venv" --skip "$WORKING_DIR/.venv" "$WORKING_DIR"

# 3. Lint and Fix with Ruff
echo -e "${BLUE}Step 3: Linting and fixing with Ruff...${NC}"
ruff check --fix --config="$WORKING_DIR/pyproject.toml" --exclude "$WORKING_DIR/venv" --exclude "$WORKING_DIR/.venv" "$WORKING_DIR"

# 4. Security scan with Bandit
echo -e "${BLUE}Step 4: Running security scan with Bandit...${NC}"
bandit -c "$WORKING_DIR/pyproject.toml" -r "$WORKING_DIR" --exclude "$WORKING_DIR/venv,$WORKING_DIR/.venv"

# 5. Run pre-commit hooks on all files
echo -e "${BLUE}Step 5: Running all pre-commit hooks...${NC}"
# Use /tmp for HOME to avoid permission issues in Codespaces
export HOME=/tmp
if command -v pre-commit &> /dev/null; then
    pre-commit run --all-files
else
    echo -e "${YELLOW}Warning: pre-commit not found. Skipping pre-commit hooks.${NC}"
fi

echo -e "${GREEN}✅ All checks passed and fixes applied!${NC}"
echo -e "${YELLOW}You can now safely run: git add -A && git commit -m \"your message\"${NC}"
