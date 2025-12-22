# Pre-commit Hooks Seup Guide

This document explains the automated code quality checks configured for the CIAL project.

## What is Pre-commit?

Pre-commit is a framework that manages and maintains multi-language pre-commit hooks. These hooks run automatically before you commit code, ensuring code quality standards are met.

## Installed Hooks

### 1. **Black** - Code Formatter
- **Purpose**: Enforces consistent Python code formatting
- **Config**: Line length 100 characters
- **When**: Before every commit
- **Auto-fix**: Yes

### 2. **isort** - Import Sorter
- **Purpose**: Automatically sorts and organizes Python imports
- **Config**: Black-compatible profile, line length 100
- **When**: Before every commit
- **Auto-fix**: Yes

### 3. **Ruff** - Fast Python Linter
- **Purpose**: Fast linting for Python code
- **Checks**:
  - `B904`: Exception chaining (raise ... from e)
  - `F541`: f-strings without placeholders
  - `UP006`, `UP045`: Modern type annotations (dict vs Dict, X | None vs Optional[X])
  - `E`, `F`, `W`: PEP 8 style errors, warnings
  - `C90`: Code complexity
  - `I`: Import conventions
  - `N`: Naming conventions
  - `B`: Bugbear checks
  - `A`: Avoid shadowing built-ins
- **When**: Before every commit
- **Auto-fix**: Yes, with --fix flag

### 4. **Bandit** - Security Linter
- **Purpose**: Finds common security issues in Python code
- **Config**: Uses pyproject.toml configuration
- **When**: Before every commit
- **Auto-fix**: No (requires manual fixes)

### 5. **YAML Lint**
- **Purpose**: Validates YAML file syntax
- **Config**: Max line length 120
- **When**: Before every commit
- **Auto-fix**: No

### 6. **General File Checks**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON validation
- Large file detection (>500KB)
- Merge conflict detection
- Case conflict detection
- Line ending normalization (LF)

## Installation

### First Time Setup

```bash
# 1. Navigate to the cial directory
cd cial

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install pre-commit (if not already installed)
pip install pre-commit

# 4. Install the git hooks
cd .. && export HOME=/tmp && pre-commit install
```

### Using Makefile (Recommended)

```bash
cd cial
make setup-pre-commit
```

## Usage

### Automatic (Default)

Once installed, pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
# Hooks run automatically here ✅
```

If any hook fails:
1. The commit is blocked
2. Auto-fixable issues are corrected automatically
3. You need to stage the fixed files and commit again

Example workflow:
```bash
git add .
git commit -m "Add new feature"
# Black reformats some files
# ruff fixes import order
git add .  # Stage the auto-fixed files
git commit -m "Add new feature"  # Try again
# ✅ Commit succeeds
```

### Manual Run

Run hooks on all files without committing:

```bash
# Using pre-commit directly
cd .. && export HOME=/tmp && pre-commit run --all-files

# Using Makefile
cd cial && make pre-commit-run
```

Run hooks on specific files:

```bash
cd .. && export HOME=/tmp && pre-commit run --files cial/api/v1/intelligence.py
```

Run a specific hook:

```bash
cd .. && export HOME=/tmp && pre-commit run black --all-files
```

## Makefile Commands

All code quality commands are available via Makefile:

```bash
cd cial

# Format code
make format          # Run Black + isort

# Linting
make lint            # Run ruff checks
make lint-fix        # Run ruff with auto-fix

# Type checking
make type-check      # Run mypy

# Security scanning
make security        # Run bandit + safety

# Run all checks
make check-all       # format + lint + type-check

# Pre-commit
make pre-commit-run  # Run all pre-commit hooks
```

## Common Issues & Solutions

### 1. Pre-commit Install Fails (Permission Denied)

**Problem**: PermissionError: [Errno 13] Permission denied: '/home/codespace'

**Solution**: Set HOME environment variable:
```bash
export HOME=/tmp && pre-commit install
```

Or use the Makefile which handles this automatically:
```bash
make setup-pre-commit
```

### 2. Commit Blocked by Black

**Problem**: Black reformats your code, but commit fails

**Solution**: Stage the reformatted files:
```bash
git add .
git commit -m "Your message"  # Try again
```

### 3. Ruff Reports Unfixable Issues

**Problem**: Some linting issues require manual fixes

**Solution**: Read the error message and fix manually:
```bash
# Example: B904 exception chaining
# Before:
except Exception as e:
    raise ValueError("Failed")

# After:
except Exception as e:
    raise ValueError("Failed") from e
```

### 4. MyPy Type Errors

**Problem**: Type hints are incorrect or missing

**Solution**: Add proper type hints:
```python
# Before
def get_data(id):
    return data

# After
def get_data(id: str) -> dict[str, Any]:
    return data
```

### 5. Skip Hooks Temporarily (Not Recommended)

If you absolutely need to skip hooks:

```bash
git commit --no-verify -m "Emergency fix"
```

**Warning**: This bypasses all quality checks. Use only in emergencies!

## Configuration Files

### `.pre-commit-config.yaml`
Main configuration file at repository root. Defines:
- Which hooks to run
- Hook versions
- Arguments for each tool
- File patterns to match
- Files to exclude

### `cial/pyproject.toml`
Python project configuration including:
- Black settings
- isort settings
- Bandit settings
- MyPy settings

## CI/CD Integration

Pre-commit hooks also run in CI/CD pipeline:

1. **GitHub Actions**: `.github/workflows/deploy.yml`
   - Runs on every PR
   - Runs on push to main/develop
   - Includes: lint, security, test, build jobs

2. **Pre-commit.ci** (Optional)
   - Automatically runs hooks on PRs
   - Auto-fixes and commits changes
   - Updates hook versions weekly

## Best Practices

### 1. Run Checks Before Committing

```bash
# Quick check
make format && make lint

# Full check
make check-all
```

### 2. Keep Dependencies Updated

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update Python packages
pip install --upgrade -r requirements-dev.txt
```

### 3. Configure Your Editor

**VS Code** (`.vscode/settings.json`):
```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

**PyCharm**:
- Settings → Tools → Black → Enable "On code reformat"
- Settings → Tools → File Watchers → Add ruff watcher

### 4. Commit Message Guidelines

Good commit messages after pre-commit fixes:

```bash
# ✅ Good
git commit -m "Add price caching feature

- Implement Redis caching for price data
- Add cache invalidation logic
- Update tests for caching behavior"

# ❌ Bad
git commit -m "fix stuff"
```

## Troubleshooting

### View Hook Logs

```bash
# See what pre-commit is doing
pre-commit run --all-files --verbose
```

### Clear Pre-commit Cache

```bash
pre-commit clean
pre-commit gc
```

### Reinstall Hooks

```bash
pre-commit uninstall
pre-commit install
```

### Test Individual Hooks

```bash
# Test just Black
pre-commit run black --all-files

# Test just Ruff
pre-commit run ruff --all-files
```

## Performance Tips

Pre-commit can be slow on large codebases:

### 1. Run Only on Changed Files (Default)

```bash
# Fast: Only checks staged files
git commit
```

### 2. Skip Slow Hooks During Development

```bash
# Skip mypy temporarily
SKIP=mypy git commit -m "WIP: Add feature"
```

### 3. Use File Caching

Pre-commit automatically caches results. Clear cache if needed:
```bash
pre-commit clean
```

## Summary

**Pre-commit hooks ensure**:
- ✅ Consistent code formatting (Black)
- ✅ Organized imports (isort)
- ✅ Clean code (Ruff)
- ✅ Type safety (MyPy)
- ✅ Security (Bandit)
- ✅ No trailing whitespace, proper line endings
- ✅ Valid YAML/JSON

**Result**: Higher code quality, fewer CI failures, faster reviews!

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

---

**Questions?** Check the [CIAL Development Guide](../docs/MODERNIZATION_PROGRESS.md) or ask in the team chat.
