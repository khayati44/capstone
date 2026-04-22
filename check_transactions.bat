@echo off
echo Checking what transactions were extracted...
echo.
echo Please enter your JWT token from the browser:
echo (Open browser DevTools, go to Application tab, look for localStorage token)
echo.
set /p TOKEN="Paste token here: "

echo.
echo Fetching transactions from upload_id=1...
curl -H "Authorization: Bearer %TOKEN%" http://localhost:8000/api/debug/transactions?upload_id=1

echo.
echo.
echo If you see error, try upload_id=2 or 3
pause
