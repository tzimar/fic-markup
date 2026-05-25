import subprocess
import sys
from pathlib import Path

files = list(Path("examples").glob("*.ffml"))

success_map: dict[Path, bool] = {file: False for file in files}

for file in files:
    try:
        result = subprocess.run(
            ["python", "parse.py", str(file)], capture_output=True, timeout=5
        )
        with open(file.with_suffix(".json"), "w", encoding="utf8") as f:
            f.write(result.stdout.decode())
    except:
        print(f"Error running parse.py on {file}:\n{result.stderr}")

        continue
