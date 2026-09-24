<#
    Buduje VoiceFlow.exe przez PyInstaller.
    Mozna uruchomic z dowolnego katalogu roboczego.
    Python: -Python <sciezka>, inaczej .venv z folderu repo, inaczej python z PATH.
#>

param(
    [string]$Python
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$SpecPath = Join-Path $RepoRoot "packaging\windows\voiceflow.spec"
$DistPath = Join-Path $RepoRoot "dist\windows"
$WorkPath = Join-Path $RepoRoot "build\windows"
$ExePath = Join-Path $DistPath "VoiceFlow.exe"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if ($Python) {
    if (Test-Path -LiteralPath $Python -PathType Container) {
        $SuggestedExe = Join-Path $Python "Scripts\python.exe"
        Write-Host "BŁĄD: $Python podany w -Python to folder, nie plik z Pythonem. Podaj plik .exe, np. $SuggestedExe." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        Write-Host "BŁĄD: nie ma pliku $Python podanego w -Python." -ForegroundColor Red
        exit 1
    }
    $Py = $Python
    $PySource = "podany parametrem -Python"
} elseif (Test-Path $VenvPython) {
    $Py = $VenvPython
    $PySource = "folder .venv w repo"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Py = "python"
    $PySource = "python z PATH, bo w repo nie ma folderu .venv"
} else {
    Write-Host "BŁĄD: nie znaleziono Pythona (brak folderu .venv w repo i brak komendy python). Zrób kroki z sekcji Instalacja w README.md." -ForegroundColor Red
    exit 1
}

# Pierwsze wywolanie sprawdza tez, czy to prawdziwy Python, a nie alias Microsoft Store (kod 9009).
$PyExe = & $Py -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0 -or -not $PyExe) {
    Write-Host ""
    Write-Host "BŁĄD: nie udało się uruchomić Pythona ($Py). Zrób kroki z sekcji Instalacja w README.md." -ForegroundColor Red
    exit 1
}
$PyVersion = & $Py -c "import platform; print(platform.python_version())"
Write-Host "Python: $PyExe ($PyVersion, $PySource)"

# Import w try/except zamiast 2>$null: w PS 5.1 przekierowanie stderr przy ErrorActionPreference=Stop konczy skrypt.
$Preflight = @'
import importlib
missing = []
for name in ['PyInstaller', 'PyQt6', 'pynput', 'pyaudio', 'requests', 'anthropic']:
    try:
        importlib.import_module(name)
    except Exception:
        missing.append(name)
print(', '.join(missing))
'@
$Missing = & $Py -c $Preflight
if ($LASTEXITCODE -ne 0) {
    Write-Host "BŁĄD: nie udało się sprawdzić modułów w Pythonie $PyExe." -ForegroundColor Red
    exit 1
}
if ($Missing) {
    Write-Host "BŁĄD: w tym Pythonie brakuje modułów: $Missing. Build bez nich dałby VoiceFlow.exe, który się nie uruchamia." -ForegroundColor Red
    Write-Host "Użyty Python: $PyExe ($PySource)." -ForegroundColor Red
    Write-Host "Co zrobić: wykonaj kroki 3 i 4 z sekcji Instalacja w README.md (w folderze repo utwórz .venv, jeśli go nie ma, i uruchom .venv\Scripts\python -m pip install -r requirements/windows.txt), potem uruchom build ponownie. Aktywować .venv nie trzeba, skrypt sam go znajdzie." -ForegroundColor Red
    exit 1
}

$BlockingProcess = Get-Process -Name VoiceFlow -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and ($_.Path -ieq $ExePath)
}

if ($BlockingProcess) {
    Write-Host "BŁĄD: VoiceFlow z dist\windows jest uruchomiony i blokuje nadpisanie pliku. Zamknij go (prawy klik na ikonie w zasobniku > Quit) i uruchom build ponownie." -ForegroundColor Red
    exit 1
}

Write-Host "Buduję VoiceFlow.exe (PyInstaller) - to potrwa kilka minut, nie zamykaj okna." -ForegroundColor Cyan

# PyInstaller pisze linie INFO na stderr; przy ErrorActionPreference=Stop i przekierowaniu
# (np. 2>&1 | Tee-Object) stają się one błędami kończącymi skrypt. Na czas wywołania
# przełączamy na Continue, wynik i tak sprawdzamy przez $LASTEXITCODE.
$ErrorActionPreference = "Continue"
& $Py -m PyInstaller $SpecPath --distpath $DistPath --workpath $WorkPath
$ExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"

if ($ExitCode -ne 0) {
    Write-Host "BŁĄD: build zakończył się kodem $ExitCode." -ForegroundColor Red
    Write-Host "Przewiń w górę do pierwszej linii z ERROR albo Traceback. Jeśli nic Ci nie mówi, skopiuj ostatnie ok. 30 linii tego okna i wyślij autorowi." -ForegroundColor Red
    exit $ExitCode
}

if (-not (Test-Path $ExePath)) {
    Write-Host "BŁĄD: PyInstaller zwrócił kod 0, ale nie znaleziono $ExePath." -ForegroundColor Red
    exit 1
}

$ExeInfo = Get-Item $ExePath
$Timestamp = $ExeInfo.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")

Write-Host "OK: build zakończony powodzeniem." -ForegroundColor Green
Write-Host "Plik: $($ExeInfo.FullName)"
Write-Host "Czas modyfikacji: $Timestamp"

$OtherRunningProcesses = Get-Process -Name VoiceFlow -ErrorAction SilentlyContinue | Where-Object {
    -not ($_.Path -and ($_.Path -ieq $ExeInfo.FullName))
}

if ($OtherRunningProcesses) {
    $OtherPaths = $OtherRunningProcesses | ForEach-Object { if ($_.Path) { $_.Path } else { "nieznana ścieżka" } } | Select-Object -Unique
    foreach ($ProcPath in $OtherPaths) {
        Write-Host "Uwaga: działa inna kopia VoiceFlow ($ProcPath). Nowy build nie wystartuje, dopóki jej nie zamkniesz (prawy klik na ikonie w zasobniku > Quit)." -ForegroundColor Yellow
    }
}

$AutostartValue = $null
try {
    $AutostartValue = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "VoiceFlow" -ErrorAction Stop).VoiceFlow
} catch {
    $AutostartValue = $null
}

if ($AutostartValue) {
    $AutostartPath = $AutostartValue.Trim('"')
    if ($AutostartPath -ine $ExeInfo.FullName) {
        Write-Host "Uwaga: autostart Windows uruchamia $AutostartPath, a nie ten build. Żeby to zmienić: 1) zamknij działający VoiceFlow (prawy klik na ikonie w zasobniku > Quit), 2) uruchom $($ExeInfo.FullName), 3) w Settings wyłącz i włącz Start with Windows." -ForegroundColor Yellow
    }
}

$OldDistExePath = Join-Path $RepoRoot "dist\VoiceFlow.exe"
if (Test-Path $OldDistExePath) {
    Write-Host "Uwaga: w dist\VoiceFlow.exe leży stary build sprzed zmiany folderów. Nowy jest w dist\windows\. Stary usuń dopiero, gdy autostart nie wskazuje już na niego (patrz kroki w uwadze o autostarcie wyżej)." -ForegroundColor Yellow
}

exit 0
