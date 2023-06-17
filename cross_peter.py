'''
vorgaengig in cmd.exe:
pip install mpy-cross-v6



'''


import mpy_cross

mpy_cross.run(*args, **kwargs)

import subprocess
proc = mpy_cross.run('--version', stdout=subprocess.PIPE)