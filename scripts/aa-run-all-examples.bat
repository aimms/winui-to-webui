echo on

rem cd C:\u\s\nirvana\02\0287dev\0287-w2wpy

set BAT_FOLDER=%~dp0
cd %BAT_FOLDER%
cd ..

pwsh -File .\scripts\run_all_examples.ps1

pause