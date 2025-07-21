#!/usr/bin/env python3
"""Prepare mcp-logger-utils for PyPI upload."""

import subprocess
import sys
from pathlib import Path

print("🚀 Preparing mcp-logger-utils for PyPI upload...")

# Steps to upload to PyPI:

print("\n1️⃣  First, ensure you have the necessary tools:")
print("   pip install --upgrade build twine")

print("\n2️⃣  Update version in pyproject.toml if needed (current: 0.1.0)")

print("\n3️⃣  Build the package:")
print("   python -m build")

print("\n4️⃣  Test the package locally:")
print("   pip install dist/mcp_logger_utils-0.1.0-py3-none-any.whl")

print("\n5️⃣  Upload to TestPyPI first (recommended):")
print("   python -m twine upload --repository testpypi dist/*")
print("   Test install: pip install --index-url https://test.pypi.org/simple/ mcp-logger-utils")

print("\n6️⃣  Upload to PyPI:")
print("   python -m twine upload dist/*")

print("\n📝 Additional steps:")
print("   - Create a PyPI account at https://pypi.org/account/register/")
print("   - Generate API token at https://pypi.org/manage/account/token/")
print("   - Create ~/.pypirc file with your credentials")

print("\n📄 Example ~/.pypirc:")
print("""
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
""")

print("\n🔧 After upload, update your MCP servers to use:")
print("   from mcp_logger_utils import MCPLogger, debug_tool")
print("   Instead of the local import")

# Optionally run the build now
if "--build" in sys.argv:
    print("\n🏗️  Building package...")
    subprocess.run([sys.executable, "-m", "build"], check=True)
    print("✅ Package built successfully!")
    print("📦 Check dist/ directory for the built files")