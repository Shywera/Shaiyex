@echo off
title Push blacklist
cd /d "%~dp0"
echo.
echo  Pushing public\blacklist.json to shaiyex.com
echo  -------------------------------------------
echo.
git add public/blacklist.json
git commit -m "Blacklist update" 2>nul || echo  (nothing changed)
git push origin main
echo.
echo  Done. The site updates in about half a minute.
echo.
pause
