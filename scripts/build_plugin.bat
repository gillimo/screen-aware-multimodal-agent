@echo off
echo Building RuneLite Session Stats plugin...
cd /d "%~dp0..\runelite_plugin"

REM Check if Gradle wrapper exists, if not use system gradle
if exist "gradlew.bat" (
    call gradlew.bat build
) else (
    where gradle >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Gradle not installed. Install from https://gradle.org/install/
        exit /b 1
    )
    gradle build
)

if exist "build\libs\*.jar" (
    echo.
    echo Built successfully!
    echo JAR location: build\libs\
    echo.
    echo To install in RuneLite:
    echo 1. Open RuneLite
    echo 2. Click the wrench icon (Configuration)
    echo 3. Search for "Plugin Hub"
    echo 4. Click the folder icon to open plugin folder
    echo 5. Copy the JAR to that folder
    echo 6. Restart RuneLite
) else (
    echo Build failed.
    exit /b 1
)
