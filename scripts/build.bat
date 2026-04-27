@echo off
setlocal

cd /d %~dp0\..

if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist dist\Shannon.exe del /f /q dist\Shannon.exe

pyinstaller --onefile --name Shannon run.py
echo Build completed: dist\Shannon.exe

endlocal
