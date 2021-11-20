"""
Proxy module which executes Python file passed in arguments. Backslashes in
file path are converted to forward slashs.
Path variables in VS Code use system path separator so they cannot be used
to start debugging in Docker.

To debug current file in Docker "docker-run" task should be modified like this:
    ...
    "python": {
        "args": ["${relativeFile}", "arg1", "arg2", ...],
        "file": "docker_import.py"
    }
See also:
    VS Code command "Docker: Add Docker Files to Workspace..."
    https://code.visualstudio.com/docs/containers/debug-common
    https://code.visualstudio.com/docs/containers/debug-python
    Related: https://stackoverflow.com/questions/63910258/vscode-copy-relative-path-with-posix-forward-slashes
"""

import importlib.util
import os
import sys
from pathlib import Path

sys.argv.pop(0)  # remove docker_import.py from argv
sys.argv[0] = sys.argv[0].replace("\\", "/")  # convert path separator
file_path = Path(sys.argv[0])
if Path(__file__) == file_path:
    raise RuntimeError("Cannot start docker_import.py file (recursion)")

os.chdir(file_path.parent)
sys.path.insert(0, '')  # import modules from current directory

spec = importlib.util.spec_from_file_location('__main__', file_path.name)
mod = importlib.util.module_from_spec(spec)
sys.modules["__main__"] = mod
spec.loader.exec_module(mod)
