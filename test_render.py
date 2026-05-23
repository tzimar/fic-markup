#!/usr/bin/env python3
"""Integration test for parse → render pipeline."""

import subprocess
import sys
from pathlib import Path

examples_dir = Path("examples")
passed = 0
failed = 0
errors = []

for ffml_file in sorted(examples_dir.glob("*.ffml")):
    html_expected = ffml_file.with_suffix(".html")
    if not html_expected.exists():
        continue
    
    # Render using our renderer
    result = subprocess.run(
        [sys.executable, "render.py", str(ffml_file)],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        failed += 1
        errors.append(f"{ffml_file.name}: Render error - {result.stderr}")
        continue
    
    # Basic validation: check that output is valid HTML-ish
    output = result.stdout
    if "<" not in output and ffml_file.name != "empty.ffml":
        failed += 1
        errors.append(f"{ffml_file.name}: No HTML tags in output")
        continue
    
    # Check for balanced tags in a simple way
    open_tags = output.count("<")
    close_tags = output.count(">")
    if open_tags != close_tags:
        failed += 1
        errors.append(f"{ffml_file.name}: Unbalanced tags ({open_tags} open, {close_tags} close)")
        continue
    
    passed += 1
    print(f"✓ {ffml_file.name}")

print(f"\nResults: {passed} passed, {failed} failed")
if errors:
    print("\nErrors:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
