@echo off
REM Build Rust core with MSVC toolchain
REM Temporarily remove Git from PATH to avoid link.exe conflict

setlocal

REM Store original path
set ORIGPATH=%PATH%

REM Remove Git paths from PATH
set PATH=%PATH:C:\Program Files\Git\usr\bin;=%
set PATH=%PATH:C:\Program Files\Git\bin;=%
set PATH=%PATH:C:\Program Files\Git\mingw64\bin;=%

cd /d "%~dp0\..\rust_core"
cargo build --release

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    copy /Y "target\release\osrs_core.dll" "..\osrs_core.pyd"
    echo Copied osrs_core.dll to osrs_core.pyd
) else (
    echo Build failed with error %ERRORLEVEL%
)

endlocal
