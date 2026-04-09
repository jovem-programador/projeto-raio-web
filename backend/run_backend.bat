@echo off
cd /d %~dp0backend
set REDIS_URL=redis://localhost:6379/0
set ODA_PATH=C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe
set SECRET_KEY=coloque-uma-chave-forte-aqui

uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --limit-max-requests 1000 --timeout-keep-alive 120