@echo off
chcp 65001 >nul
setlocal
title KBO 8-BIT BASEBALL - Update ^& Run

REM ============================================================
REM  이 배치 파일이 있는 폴더로 이동 (어디서 실행하든 안전)
REM ============================================================
cd /d "%~dp0"

set BRANCH=main

echo ============================================================
echo   최신 버전으로 업데이트 중... (%BRANCH%)
echo ============================================================
git pull origin %BRANCH%
if errorlevel 1 (
    echo.
    echo [!] git pull 실패. 인터넷/깃 설정을 확인하세요.
    echo     그래도 현재 버전으로 계속 실행합니다.
    echo.
)

echo.
echo ============================================================
echo   pygame 확인 / 설치...
echo ============================================================
python -c "import pygame" 2>nul
if errorlevel 1 (
    echo pygame 미설치 - 설치를 시작합니다.
    python -m pip install pygame
)

echo.
echo ============================================================
echo   KBO 8-BIT BASEBALL 실행!
echo   방향키 조준  ^|  SPACE 스윙  ^|  ESC 뒤로  ^|  F1 스캔라인
echo ============================================================
python -m kbo_ball

echo.
echo 게임이 종료되었습니다. 창을 닫으려면 아무 키나 누르세요.
pause >nul
endlocal
