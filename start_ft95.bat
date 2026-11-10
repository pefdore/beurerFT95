@echo off

:: Lancement du premier script (MedicalAppLauncher)
cd /d C:\Users\pfdor\Documents\MedicalAppLauncher
start /b pythonw.exe launch_all.py

:: Lancement du second script (BP2Pro)
cd /d C:\BP2Pro
start /b pythonw.exe launch_bp2_pro.py

:: Lancement du widget temperature FT95 (module installe : pip install -e .)
cd /d C:\Users\pfdor\beurerFT95
start "" pythonw.exe -m ft95 widget

exit
