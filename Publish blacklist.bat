@echo off
title Publish blacklist
cd /d "%~dp0"

echo.
echo  Reading blacklist.xlsx and publishing to shaiyex.com
echo  ---------------------------------------------------
echo.

python "tools\publish.py"
if errorlevel 1 (
  echo.
  echo  Something went wrong. Nothing was published.
)

echo.
pause
