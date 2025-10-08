@echo off
REM Private PyPI 배포 스크립트 (Windows Batch)

setlocal enabledelayedexpansion

echo 🚀 Aegis Shared Library - Private PyPI Deployment
echo.

REM Python 설치 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Poetry 설치 확인
poetry --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Poetry is not installed or not in PATH
    echo Please install Poetry and try again
    pause
    exit /b 1
)

echo ✅ Python and Poetry are available

REM 인자 처리
set "REPOSITORY=private-pypi"
set "BUMP_TYPE="
set "FORCE="
set "SKIP_BUILD="

:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="--repository" (
    set "REPOSITORY=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--bump" (
    set "BUMP_TYPE=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--force" (
    set "FORCE=--force"
    shift
    goto :parse_args
)
if "%~1"=="--skip-build" (
    set "SKIP_BUILD=--skip-build"
    shift
    goto :parse_args
)
shift
goto :parse_args
:end_parse

echo 📋 Configuration:
echo    Repository: %REPOSITORY%
if defined BUMP_TYPE echo    Version Bump: %BUMP_TYPE%
if defined FORCE echo    Force: Yes
if defined SKIP_BUILD echo    Skip Build: Yes
echo.

REM Python 스크립트 실행
set "CMD=python scripts/deploy-private.py --repository %REPOSITORY%"
if defined BUMP_TYPE set "CMD=!CMD! --bump %BUMP_TYPE%"
if defined FORCE set "CMD=!CMD! %FORCE%"
if defined SKIP_BUILD set "CMD=!CMD! %SKIP_BUILD%"

echo 🚀 Executing: %CMD%
echo.

%CMD%

if errorlevel 1 (
    echo.
    echo ❌ Deployment failed
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Deployment completed successfully!
)

pause