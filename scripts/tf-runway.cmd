@echo OFF
REM="""
setlocal
set PythonExe=""
set PythonExeFlags=

for %%i in (cmd bat exe) do (
    for %%j in (python.%%i) do (
        call :SetPythonExe "%%~$PATH:j"
    )
)
for /f "tokens=2 delims==" %%i in ('assoc .py') do (
    for /f "tokens=2 delims==" %%j in ('ftype %%i') do (
        for /f "tokens=1" %%k in ("%%j") do (
            call :SetPythonExe %%k
        )
    )
)
%PythonExe% -x %PythonExeFlags% "%~f0" %*
exit /B %ERRORLEVEL%
goto :EOF

:SetPythonExe
if not ["%~1"]==[""] (
    if [%PythonExe%]==[""] (
        set PythonExe="%~1"
    )
)
goto :EOF
"""

# ===================================================
# Python script starts here
# Above helper adapted from https://github.com/aws/aws-cli/blob/1.11.121/bin/aws.cmd
# ===================================================

#!/usr/bin/env python
from __future__ import print_function
import subprocess
import sys

from runway.env_mgr.tfenv import TFEnvManager


if __name__ == "__main__":
    # No immediate plans to remove. Not to be done prior to 2.0
    print('DEPRECATION NOTICE: the "tf-runway" command has been deprecated '
          'in favor of "runway tfenv run"', file=sys.stderr)
    tf_bin = TFEnvManager().install()
    sys.exit(subprocess.call([tf_bin] + sys.argv[1:]))
