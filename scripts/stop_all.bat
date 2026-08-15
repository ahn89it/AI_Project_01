@echo off
REM run_all.bat로 띄운 서비스들과 Tomcat(도서관 사이트)까지 전부 정지한다.
REM 포트를 점유 중인 프로세스를 찾아 강제 종료하는 방식이라, 어떻게 켰든(더블클릭/PowerShell 등) 상관없이 잡는다.
setlocal enabledelayedexpansion

echo === 실행 중인 서비스 종료 ===

call :kill_port 8501 "Streamlit"
call :kill_port 8000 "FastAPI"
call :kill_port 8080 "Tomcat"
call :kill_port 3307 "MariaDB"
call :kill_port 11434 "Ollama"

echo.
echo 종료 완료.
pause
exit /b 0

:kill_port
set "PORT=%~1"
set "NAME=%~2"
set "FOUND=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
    set "FOUND=1"
    echo   %NAME% [PID %%p] 종료함.
)
if "!FOUND!"=="0" echo   %NAME%는 이미 꺼져 있음.
exit /b 0
