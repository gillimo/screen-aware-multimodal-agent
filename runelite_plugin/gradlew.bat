@rem Gradle wrapper script for Windows
@rem Downloads Gradle if not present

@if "%DEBUG%"=="" @echo off
setlocal EnableDelayedExpansion

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.

set GRADLE_USER_HOME=%USERPROFILE%\.gradle
set WRAPPER_JAR=%DIRNAME%gradle\wrapper\gradle-wrapper.jar

@rem Download wrapper jar if missing
if not exist "%WRAPPER_JAR%" (
    echo Downloading Gradle wrapper...
    mkdir "%DIRNAME%gradle\wrapper" 2>nul
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/gradle/gradle/raw/v8.5.0/gradle/wrapper/gradle-wrapper.jar' -OutFile '%WRAPPER_JAR%'"
)

@rem Find Java
set JAVA_EXE=java.exe
if defined JAVA_HOME (
    set JAVA_EXE=%JAVA_HOME%\bin\java.exe
)

@rem Run Gradle
"%JAVA_EXE%" -jar "%WRAPPER_JAR%" %*
