@echo off
echo Building Rust core module...
cd /d "%~dp0..\rust_core"

REM Check if Rust is installed
where cargo >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Rust not installed. Install from https://rustup.rs/
    exit /b 1
)

REM Build release
cargo build --release

REM Copy to Python can find it
if exist "target\release\osrs_core.dll" (
    copy "target\release\osrs_core.dll" "..\osrs_core.pyd"
    echo Built successfully! osrs_core.pyd ready.
) else (
    echo Build failed or .dll not found.
    exit /b 1
)
