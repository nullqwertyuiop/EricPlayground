@echo off

:pdm
pdm run textual run --dev .\tui.py
pause
goto pdm
