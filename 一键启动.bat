@echo off
setlocal
title Zhilv Cloud Trip - One-click Launcher
set "ROOT=%~dp0"
set "PY=%ROOT%ai-service\.venv\Scripts\python.exe"
set "REDIS_DIR=D:\Redis-8.10.1"
set "SKIP_MILVUS=0"
if /i "%~1"=="--skip-milvus" set "SKIP_MILVUS=1"

echo ==============================================
echo   Zhilv Cloud Trip  One-click Launcher
echo   Project root: %ROOT%
echo   Option: --skip-milvus   skip Milvus (no RAG)
echo   Ports already running are auto-skipped. Safe to rerun.
echo ==============================================
echo.

rem ---------- MySQL (expected to run as a Windows service) ----------
netstat -ano | findstr /C:":3306 " >nul 2>&1
if errorlevel 1 (
  echo [x] MySQL :3306 is NOT listening. Please start the MySQL service first, then rerun this script.
  goto end_fail
)
echo [ok] MySQL    :3306

rem ---------- Redis ----------
netstat -ano | findstr /C:":6379 " >nul 2>&1
if errorlevel 1 (
  if not exist "%REDIS_DIR%\redis-server.exe" (
    echo [x] Redis not found: "%REDIS_DIR%\redis-server.exe". Edit REDIS_DIR at the top of this script.
    goto end_fail
  )
  echo [..] Starting Redis in a new window...
  start "Redis-6379" /D "%REDIS_DIR%" cmd /k "redis-server.exe"
) else (
  echo [ok] Redis   :6379 already running
)

rem ---------- Milvus (optional, RAG only; failure does not block the app) ----------
if "%SKIP_MILVUS%"=="1" (
  echo [..] Milvus : skipped via --skip-milvus
) else (
  docker info >nul 2>&1
  if errorlevel 1 (
    echo [x] Milvus : Docker Desktop not running, skipped - chat runs without a knowledge base
  ) else (
    echo [..] Starting Milvus in a new window...
    start "Milvus-19530" /D "%ROOT%deploy\milvus" cmd /k "docker-compose up -d"
  )
)

rem ---------- ai-service ----------
echo [..] Starting ai-service in a new window...
start "ai-service-8100" /D "%ROOT%ai-service" cmd /k ""%PY%" -m uvicorn app.main:app --port 8100"

rem ---------- backend ----------
echo [..] Starting backend in a new window...
start "backend-8080" /D "%ROOT%backend" cmd /k ""%ROOT%backend\mvnw.cmd" spring-boot:run"

rem ---------- frontend ----------
echo [..] Starting frontend in a new window...
start "frontend-5173" /D "%ROOT%frontend" cmd /k "npm run dev"

echo.
echo Waiting for services to be ready (ai-service 5-15s; backend first run 30-120s)...

rem ---- wait ai-service 8100 ----
set /a n=0
:wait_ai
curl -s -f -o nul http://127.0.0.1:8100/health >nul 2>&1
if not errorlevel 1 goto ok_ai
set /a n+=1
if %n% geq 90 goto err_ai
timeout /t 1 /nobreak >nul
goto wait_ai
:ok_ai
echo [ok] ai-service :8100 ready
goto wait_backend
:err_ai
echo [x] ai-service did not become ready in 90s. Check the ai-service-8100 window.
goto wait_backend

rem ---- wait backend 8080 (TCP listening) ----
:wait_backend
set /a n=0
:wait_be
netstat -ano | findstr /C:":8080 " >nul 2>&1
if not errorlevel 1 goto ok_be
set /a n+=1
if %n% geq 180 goto err_be
timeout /t 1 /nobreak >nul
goto wait_be
:ok_be
echo [ok] backend  :8080 ready
goto wait_frontend
:err_be
echo [x] backend did not become ready in 180s. Check the backend-8080 window, Redis must be up, no port conflict.
goto wait_frontend

rem ---- wait frontend 5173 ----
:wait_frontend
set /a n=0
:wait_fe
curl -s -f -o nul http://127.0.0.1:5173/ >nul 2>&1
if not errorlevel 1 goto ok_fe
set /a n+=1
if %n% geq 60 goto err_fe
timeout /t 1 /nobreak >nul
goto wait_fe
:ok_fe
echo [ok] frontend :5173 ready
goto summary
:err_fe
echo [x] frontend did not become ready in 60s. Check the frontend-5173 window.

:summary
echo.
echo ==============================================
echo   Open http://localhost:5173
echo   Demo account: demo_d20_01 / 123456  (or register your own)
echo.
echo   Service windows: Redis-6379 / ai-service-8100 / backend-8080 / frontend-5173
echo   Milvus-19530 is only needed for RAG; if down, chat/generation simply runs without a knowledge base.
echo   To stop: Ctrl+C in each window, or just close them. Rerun anytime; running ports are auto-skipped.
echo ==============================================
start "" http://localhost:5173
goto eof

:end_fail
echo.
echo Prerequisites not met - nothing was started. Fix and rerun this script.
goto eof

:eof
echo.
pause
endlocal
