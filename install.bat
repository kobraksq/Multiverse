@echo off

set "CURRENT_DIR=%~dp0"

cd %CURRENT_DIR%

set "MULTIVERSE_DIR=%CURRENT_DIR%multiverse"

@REM Install vckpg

if not exist "%MULTIVERSE_DIR%\external\vcpkg" (
    git clone https://github.com/Microsoft/vcpkg.git "%MULTIVERSE_DIR%\external\vcpkg"
    cd "%MULTIVERSE_DIR%\external\vcpkg"
    bootstrap-vcpkg.bat
    vcpkg integrate install
)