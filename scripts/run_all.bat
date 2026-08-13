@echo off
REM 시연 콜드스타트 스크립트: Ollama/MariaDB 확인 -> FastAPI -> Streamlit 순서로 기동한다.
setlocal
cd /d "%~dp0.."

echo [1/4] Ollama 상태 확인 중...
curl -s -o nul -w "" http://localhost:11434/api/tags
if errorlevel 1 (
    echo   Ollama가 응답하지 않습니다. 먼저 Ollama를 실행한 뒤 이 스크립트를 다시 실행하세요.
    pause
    exit /b 1
) else (
    echo   Ollama 정상 응답.
)

echo [2/4] MariaDB(3307) 상태 확인 중...
netstat -an | findstr ":3307" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo   MariaDB가 떠 있지 않아 백그라운드로 기동합니다...
    start "MariaDB" /min "C:\Program Files\MariaDB 12.3\bin\mariadbd.exe" --defaults-file="C:\Program Files\MariaDB 12.3\data\my.ini"
    timeout /t 5 /nobreak >nul
) else (
    echo   MariaDB 이미 실행 중.
)

echo [3/4] FastAPI 서버 기동 중...
start "FastAPI" cmd /k ".venv\Scripts\activate.bat && uvicorn server.main:app --host 127.0.0.1 --port 8000"

echo   FastAPI 준비 대기 중...
:wait_health
timeout /t 2 /nobreak >nul
curl -s -o nul http://127.0.0.1:8000/health
if errorlevel 1 goto wait_health
echo   FastAPI 준비 완료.

echo [4/4] Streamlit UI 기동 중...
start "Streamlit" cmd /k ".venv\Scripts\activate.bat && streamlit run ui\app.py"

echo 모든 서비스가 기동되었습니다. 각 창을 닫으면 해당 서비스가 종료됩니다.
endlocal
