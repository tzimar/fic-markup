import os
import sys

file_in = sys.argv[1]

with open(file_in, 'r') as f:
  input = f.read()

file_out: str
if len(sys.argv) > 2:
  file_out = sys.argv[2] 
else:
  file_out = os.path.splitext(file_in)[0] + '.html'

output: str = ''

# TODO: Parse txt into HTML

with open(file_out, 'w') as f:
  f.write(output)