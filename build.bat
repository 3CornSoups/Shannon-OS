@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
for %%I in ("%PROJECT_DIR%") do set "PARENT_DIR=%%~dpI"
for %%I in ("%PROJECT_DIR%") do set "PROJECT_NAME=%%~nI"

set "OUTPUT=%PARENT_DIR%%PROJECT_NAME%.zip"

cd /d "%PROJECT_DIR%"

echo ========================================
echo   ShannonOS 打包脚本
echo   输出: %OUTPUT%
echo ========================================

echo.
echo [1/2] 构建前端...
cd web
call npm run build -- --silent 2>nul
if %errorlevel% neq 0 (
    echo 前端构建失败，尝试继续...
)
cd ..

echo.
echo [2/2] 创建压缩包...

powershell -Command ^
  "$exclude = @(" ^
    "'.venv/*'","'.venv/**'","'.venv/'", ^
    "'node_modules/*'","'node_modules/**'","'node_modules/'", ^
    "'__pycache__/*'","'__pycache__/**'","'__pycache__/'", ^
    "'*.pyc'","'*.pyo'","'*.pyd'", ^
    "'.git/*'","'.git/**'","'.git/'", ^
    "'.trae/*'","'.trae/**'","'.trae/'", ^
    "'.claude/*'","'.claude/**'","'.claude/'", ^
    "'web/node_modules/*'","'web/node_modules/**'","'web/node_modules/'", ^
    "'data/*'","'data/**'","'data/'", ^
    "'PRD_*'", ^
    "'*.zip'","'*.tar.gz'" ^
  ");" ^
  "$files = Get-ChildItem -Recurse -File | Where-Object {" ^
    "$full = $_.FullName.Replace([IO.Path]::GetFullPath('.').TrimEnd('\') + '\', '').Replace('\', '/');" ^
    "-not ($exclude | Where-Object { $full -like $_ -or ($_.StartsWith('*') -and $full.EndsWith($_.Substring(1))) })" ^
  "};" ^
  "Compress-Archive -Path $files.FullName -DestinationPath '%OUTPUT%' -CompressionLevel Optimal -Force"

if exist "%OUTPUT%" (
    echo.
    echo ========================================
    echo  打包完成!
    echo  文件: %OUTPUT%
    for %%A in ("%OUTPUT%") do echo  大小: %%~zA 字节
    echo ========================================
) else (
    echo 打包失败!
    exit /b 1
)
