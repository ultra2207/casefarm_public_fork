@echo off
echo Building executable...

pyinstaller --noconsole --clean --noconfirm --add-data="C:\Users\Sivasai\Documents\GitHub\CaseFarm\database\db\database.db;." --icon="C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\executables\icons\twofa.ico" --distpath="C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\executables\dist" C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\extras\steam_mobile_code.py
echo Cleaning up build files...
del /q steam_mobile_code.spec
rmdir /s /q C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\build

echo Done! Executable is in C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\executables\dist\steam_mobile_code

:: ./utils/extras/build_code_exe.bat