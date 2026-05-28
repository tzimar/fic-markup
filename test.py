import subprocess
import sys
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Test():
    input_file: str
    expected_output_files: list[str]
    success: bool | None = None

tests: list[Test] = []

def make_test(input_file: str, expected_output_files: list[str]):
    tests.append(Test(
        input_file=input_file,
        expected_output_files=expected_output_files,
    ))

examples_dir = Path("examples/")
output_dir = Path("examples/test-output/")

output_dir.mkdir(exist_ok=True)


def run_test(test: Test) -> bool:
  
    render = subprocess.run(
        [sys.executable, "render.py", str(examples_dir / (test.input_file + ".ffml")), "-d", str(output_dir)],
        capture_output=True,
        text=True,
    )
    if render.returncode != 0:
        print(f"Error running render.py on {test.input_file}.ffml:\n{render.stderr}")
        return False

    for expected_output_file in test.expected_output_files:
      
      if not (output_dir / (expected_output_file + ".html")).exists():
          print(f"Expected output file {expected_output_file}.html does not exist for {test.input_file}.ffml.")
          return False

      expected_path = examples_dir / (expected_output_file + ".html")
      actual_path = output_dir / (expected_output_file + ".html")
      expected_text = expected_path.read_text(encoding="utf8")
      actual_text = actual_path.read_text(encoding="utf8")
      if expected_text != actual_text:
          print(f"Differences found in {expected_output_file}.html:")
          for i, (e_line, a_line) in enumerate(zip(expected_text.splitlines(), actual_text.splitlines()), start=1):
              if e_line != a_line:
                  print(f"Line {i}: expected={e_line!r}, actual={a_line!r}")
                  break
          return False
      else:
          print(f"No differences found in {expected_output_file}.html.")
    return True

def run_tests():

    for test in tests:
        test.success = run_test(test)
    
    for test in tests:
        if test.success:
            print(f"{test.input_file}.ffml: Success")
        else:
            print(f"{test.input_file}.ffml: Failure")

    successes = list(map(lambda t: t.success, tests))

    if all(successes):
        print("All tests passed!")
        sys
    else:
        print(
            f"{sum(successes)}/{len(successes)} tests failed."
        )
        sys.exit(1)


make_test("blocks", ["blocks"])
make_test("comments", ["comments"])
make_test("dialog", ["dialog"])
make_test("empty", ["empty"])
make_test("inline_formatting", ["inline_formatting"])
make_test("section_breaks", ["section_breaks"])
make_test("metadata", ["metadata"])

run_tests()