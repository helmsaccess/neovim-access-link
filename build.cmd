@echo off
setlocal
pushd "%~dp0" >nul
if errorlevel 1 (
	echo Could not open the add-on source directory.
	set "buildExit=1"
	goto finish
)

where py >nul 2>nul
if errorlevel 1 goto findPython
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 goto usePy

:findPython
where python >nul 2>nul
if errorlevel 1 goto pythonMissing
python -c "import sys" >nul 2>nul
if not errorlevel 1 goto usePython

:pythonMissing
echo A current Python 3 was not found. Install Python and try again.
set "buildExit=1"
goto finish

:usePy
py -3 build.py
set "buildExit=%errorlevel%"
goto finish

:usePython
python build.py
set "buildExit=%errorlevel%"

:finish
popd
echo.
if "%buildExit%"=="0" (
	echo The build completed successfully.
) else (
	echo The build did not complete.
)
pause
exit /b %buildExit%
