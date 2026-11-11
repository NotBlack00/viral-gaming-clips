@echo off
setlocal
cd /d "%~dp0"
title VIRAL GAMING CLIPS - Fortnite
echo ======================================================
echo        VIRAL GAMING CLIPS - MOTORE LOCALE
echo ======================================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python non trovato. Installa Python 3.11 o 3.12 da https://www.python.org/downloads/
  echo Durante l'installazione seleziona "Add Python to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3.12 -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installazione non riuscita. Controlla la connessione e riprova.
  pause
  exit /b 1
)
echo.
echo Avvio del motore sul PC...
echo Dal tablet, collegato alla stessa rete Wi-Fi, apri http://IP-DEL-PC:8501
echo Per trovare l'IP: apri un altro Prompt e digita ipconfig
echo.
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.maxUploadSize 4096 --server.maxMessageSize 4096
pause
