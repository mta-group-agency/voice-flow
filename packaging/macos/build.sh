#!/usr/bin/env bash
#
# Builds VoiceFlow.app przez PyInstaller, podpisuje ad-hoc i pakuje do zipa.
# Mozna uruchomic z dowolnego katalogu roboczego. Wymaga macOS (sips, iconutil,
# codesign, ditto to narzedzia systemowe Apple).
#
# Zaklada, ze zaleznosci Pythona sa juz zainstalowane (requirements/macos.txt zawiera
# pyobjc-framework-Quartz i pyobjc-framework-ApplicationServices, potrzebne przez pynput).
# Patrz: .github/workflows/build-macos.yml.

set -euo pipefail

err() {
    echo "BLAD: $1" >&2
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
    err "ten skrypt buduje .app i dziala tylko na macOS (PyInstaller nie robi .app z innego systemu)."
fi

PYTHON_BIN="python"
if ! command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi
command -v "$PYTHON_BIN" >/dev/null 2>&1 || err "nie znaleziono Pythona (brak komendy python ani python3)."

SPEC_PATH="$REPO_ROOT/packaging/macos/voiceflow.spec"
DIST_PATH="$REPO_ROOT/dist/macos"
WORK_PATH="$REPO_ROOT/build/macos"
APP_PATH="$DIST_PATH/VoiceFlow.app"
ZIP_PATH="$DIST_PATH/VoiceFlow-macos-arm64.zip"

ICON_PNG="$REPO_ROOT/assets/common/icon.png"
ICON_ICNS="$REPO_ROOT/assets/macos/icon.icns"
ICONSET_DIR="$WORK_PATH/icon.iconset"

if [[ ! -f "$ICON_ICNS" ]]; then
    [[ -f "$ICON_PNG" ]] || err "brak $ICON_PNG, z niego generuje sie ikona Maca."
    echo "Generuje icon.icns z $ICON_PNG (zrodlo 64px, powiekszenie do 1024px jest akceptowalne)..."
    mkdir -p "$(dirname "$ICON_ICNS")"
    rm -rf "$ICONSET_DIR"
    mkdir -p "$ICONSET_DIR"
    for size in 16 32 128 256 512; do
        double=$((size * 2))
        sips -z "$size" "$size" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}.png" >/dev/null \
            || err "sips nie wygenerowal icon_${size}x${size}.png."
        sips -z "$double" "$double" "$ICON_PNG" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" >/dev/null \
            || err "sips nie wygenerowal icon_${size}x${size}@2x.png."
    done
    iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS" || err "iconutil nie zbudowal $ICON_ICNS."
    echo "OK: icon.icns gotowe ($ICON_ICNS)."
else
    echo "icon.icns juz istnieje, pomijam generowanie ($ICON_ICNS)."
fi

echo "Buduje VoiceFlow.app (PyInstaller) - to potrwa kilka minut..."
"$PYTHON_BIN" -m PyInstaller "$SPEC_PATH" --distpath "$DIST_PATH" --workpath "$WORK_PATH" --noconfirm \
    || err "PyInstaller zakonczyl sie bledem, przewin w gore do pierwszego ERROR/Traceback."

[[ -d "$APP_PATH" ]] || err "PyInstaller zwrocil kod 0, ale nie znaleziono $APP_PATH."

echo "Podpisuje ad-hoc (codesign --force --deep --sign -)..."
codesign --force --deep --sign - "$APP_PATH" || err "codesign nie podpisal $APP_PATH."

echo "Weryfikuje podpis (codesign -dv):"
codesign -dv "$APP_PATH" 2>&1 || err "codesign -dv zglosil problem z podpisem $APP_PATH."

echo "Pakuje do zipa (ditto)..."
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH" || err "ditto nie utworzyl $ZIP_PATH."

[[ -f "$ZIP_PATH" ]] || err "ditto zwrocil kod 0, ale nie znaleziono $ZIP_PATH."

ZIP_SIZE=$(stat -f%z "$ZIP_PATH" 2>/dev/null || stat -c%s "$ZIP_PATH" 2>/dev/null || echo "?")

echo "OK: build zakonczony powodzeniem."
echo "Aplikacja: $APP_PATH"
echo "Zip: $ZIP_PATH ($ZIP_SIZE bajtow)"
