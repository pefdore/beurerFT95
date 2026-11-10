@echo off

:: Chemin absolu de Python (evite les echecs si le PATH n'est pas encore pret au demarrage)
set PYTHONW=C:\Users\pfdor\AppData\Local\Programs\Python\Python312\pythonw.exe

:: Lancement du premier script (MedicalAppLauncher)
cd /d C:\Users\pfdor\Documents\MedicalAppLauncher
start /b pythonw.exe launch_all.py

:: Lancement du second script (BP2Pro)
cd /d C:\BP2Pro
start /b pythonw.exe launch_bp2_pro.py

:: Lancement du widget temperature FT95 (une seule instance : les doublons sont ignores)
cd /d C:\Users\pfdor\beurerFT95
start "" "%PYTHONW%" -m ft95 widget

exit
