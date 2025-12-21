#!/usr/bin/env python3
"""
Comprehensive import test to catch any module-level errors before deployment.

This script attempts to import all Python modules in the cial/ directory
to ensure there are no import-time crashes like:
- AttributeError from incorrect logger usage
- Missing dependencies
- Circular imports
- Invalid syntax

Run this before every deployment to catch issues early.
"""

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import List, Tuple


def discover_modules(package_path: Path) -> list[str]:
    """
    Discover all Python modules in the package.

    Args:
        package_path: Path to the package directory

    Returns:
        List of module names (e.g., ['api.v1.intelligence', 'core.broker'])
    """
    modules = []

    # Walk through all .py files
    for py_file in package_path.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(py_file) or py_file.name.startswith("test_"):
            continue

        # Convert path to module name
        relative = py_file.relative_to(package_path.parent)
        module_parts = list(relative.parts)

        # Remove .py extension
        module_parts[-1] = module_parts[-1][:-3]

        # Skip __init__ files (they're imported with package)
        if module_parts[-1] == "__init__":
            module_parts.pop()

        if module_parts:  # If not empty after removing __init__
            module_name = ".".join(module_parts)
            modules.append(module_name)

    return sorted(modules)


def test_import(module_name: str) -> tuple[bool, str]:
    """
    Test if a module can be imported successfully.

    Args:
        module_name: Full module name (e.g., 'api.v1.intelligence')

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return False, error_msg


def main():
    """Run comprehensive import tests."""
    print("=" * 80)
    print("CIAL Import Validation Test")
    print("=" * 80)
    print()

    # Get package path
    script_dir = Path(__file__).parent
    package_path = script_dir

    print(f"Package path: {package_path}")
    print()

    # Discover all modules
    print("Discovering modules...")
    modules = discover_modules(package_path)
    print(f"Found {len(modules)} modules to test")
    print()

    # Test each module
    print("Testing imports...")
    print("-" * 80)

    passed = []
    failed = []

    for module_name in modules:
        success, error = test_import(module_name)

        if success:
            print(f"✅ {module_name}")
            passed.append(module_name)
        else:
            print(f"❌ {module_name}")
            print(f"   Error: {error}")
            print()
            failed.append((module_name, error))

    print()
    print("=" * 80)
    print("Test Results")
    print("=" * 80)
    print(f"Total modules: {len(modules)}")
    print(f"Passed: {len(passed)} ✅")
    print(f"Failed: {len(failed)} ❌")
    print()

    if failed:
        print("Failed modules:")
        print("-" * 80)
        for module_name, error in failed:
            print(f"❌ {module_name}")
            print(f"   {error}")
            print()

        print()
        print("⚠️  DEPLOYMENT NOT READY - Fix import errors above")
        sys.exit(1)
    else:
        print("✅ ALL IMPORTS SUCCESSFUL - READY FOR DEPLOYMENT")
        sys.exit(0)


if __name__ == "__main__":
    main()
