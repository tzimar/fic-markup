import subprocess
import sys
from pathlib import Path

files = list(Path('examples').glob('*.ffml'))

success_map: dict[Path, bool] = {file: False for file in files}

for file in files:
  subprocess.run(['python', 'render.py', str(file), "-o", str(file.with_suffix('.test.html'))])
  diff = subprocess.run(['diff', str(file.with_suffix('.html')), str(file.with_suffix('.test.html'))], capture_output=True, text=True)
  success_map[file] = diff.returncode == 0
  if diff.returncode != 0:
    print(f'Differences found in {file}:')
    print(diff.stdout)
  else:
    print(f'No differences found in {file}.')

if len(sys.argv) == 1 or sys.argv[1] != '--keep':
  for file in files:
    test_file = file.with_suffix('.test.html')
    if test_file.exists():
      test_file.unlink()

for file, success in success_map.items():
  if success:
    print(f'{file}: Success')
  else:
    print(f'{file}: Failure')

if all(success_map.values()):
  print('All tests passed!')
  sys
else:
  print(f'{len([f for f, s in success_map.items() if not s])}/{len(success_map)} tests failed.')
  sys.exit(1)