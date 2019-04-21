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
import logging
import sys

from runway.tfenv import TFEnv


if __name__ == "__main__":
    if len(sys.argv) in [2, 3] and sys.argv[1] == 'install':
        if len(sys.argv) == 3:
            TFEnv().install(sys.argv[2])
        else:
            TFEnv().install()
    else:
        logging.error('Use like "tfenv-runway install 0.12.0"')
        sys.exit(1)
