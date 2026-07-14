@echo off
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "[Console]::Out.Write($env:NVIM_NVDA_SSH_PASSWORD)"
