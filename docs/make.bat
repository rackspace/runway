@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=pipenv run sphinx-build
)
set SOURCEDIR=source
set BUILDDIR=build

if "%1" == "" goto help
pipenv sync
%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'pipenv' command was not found. Make sure you have pipenv
	echo.installed, then add the pipenv directory to PATH.
	echo.
	echo.If you don't have pipenv installed, use pip to install it from
	echo.pip install git+https://github.com/pypa/pipenv
	exit /b 1
)

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%

:end
popd
