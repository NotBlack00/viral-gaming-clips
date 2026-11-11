@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo      VIRAL GAMING CLIPS - INSTALLAZIONE
echo ==========================================
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
  echo Installazione non riuscita. Controlla la connessione e riprova.
  pause
  exit /b 1
)
echo.
echo Avvio dell'applicazione...
python -m streamlit run app.py
pause
