import subprocess
import sys
from pathlib import Path

files = list(Path('examples').glob('*.txt'))

success_map: dict[Path, bool] = {file: False for file in files}

for file in files:
  subprocess.run(['python', 'render.py', str(file), str(file.with_suffix('.test.html'))])
  
  # check if output file even exists
  if not file.with_suffix('.test.html').exists():
    print(f'Output file {file.with_suffix(".test.html")} does not exist.')
    continue

  # normalise files before diffing
  with file.with_suffix('.html').open() as f:
    normalised_html = ' '.join(f.read().split())
    with file.with_suffix('.expected.html').open('w') as f:
      f.write(normalised_html)
  with file.with_suffix('.test.html').open() as f:
    normalised_test_html = ' '.join(f.read().split())
    with file.with_suffix('.actual.html').open('w') as f:
      f.write(normalised_test_html)

  # show diff and record success
  result = subprocess.run(['diff', '-u', str(file.with_suffix('.expected.html')), str(file.with_suffix('.actual.html'))], capture_output=True, text=True)
  if result.returncode == 0:
    success_map[file] = True
  else:
    print(f'Diff for {file}:\n{result.stdout}')

if len(sys.argv) == 1 or sys.argv[1] != '--keep':
  for file in files:
    test_file = file.with_suffix('.test.html')
    if test_file.exists():
      test_file.unlink()
    test_file = file.with_suffix('.expected.html')
    if test_file.exists():
      test_file.unlink()
    test_file = file.with_suffix('.actual.html')
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