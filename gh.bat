@echo off
setlocal

rem ---- Check that a commit message was provided ----
if "%~1"=="" (
    echo Usage: gh "commit message"
    exit /b 1
)

rem ---- Stage all changes (including deletions) ----
git add -A

rem ---- Update your local branch from GitHub (replace "main" if your branch is different) ----
git pull origin main

rem ---- Only commit if there are staged changes ----
git diff --cached --quiet
if errorlevel 1 (
    rem %* expands to all arguments exactly as passed, including quotes
    git commit -m %*
)

rem ---- Push to GitHub ----
git push origin HEAD

rem ---- Push to other repos, e.g. DevOps. Use --force if you need to override its history ----
rem git push devops HEAD

endlocal
