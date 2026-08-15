@echo off
REM 시연 콜드스타트 스크립트: Ollama/MariaDB 확인(필요시 자동 기동) -> FastAPI -> Streamlit 순서로 기동한다.
setlocal
cd /d "%~dp0.."

echo [1/4] Ollama 상태 확인 중...
curl -s -o nul -w "" http://localhost:11434/api/tags
if not errorlevel 1 (
    echo   Ollama 이미 실행 중.
    goto ollama_done
)
echo   Ollama가 떠 있지 않아 백그라운드로 기동합니다...
start "Ollama" /min "C:\Users\gunny\AppData\Local\Programs\Ollama\ollama.exe" serve
for /l %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    curl -s -o nul http://localhost:11434/api/tags
    if not errorlevel 1 goto ollama_ready
)
echo   Ollama가 30초 내에 응답하지 않습니다. Ollama 설치 상태를 확인한 뒤 다시 실행하세요.
pause
exit /b 1
:ollama_ready
echo   Ollama 정상 응답.
:ollama_done

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
