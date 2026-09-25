# assets/macos

Ikony specyficzne dla macOS.

- `icon.icns`: ikona aplikacji `VoiceFlow.app` (wskazuje ją `packaging/macos/voiceflow.spec`).
  Generowana w momencie builda przez `packaging/macos/build.sh` (sips + iconutil z `assets/common/icon.png`),
  ignorowana przez git.
- monochromatyczne ikony template dla paska menu (menu bar): na razie z `assets/common`, docelowo
  tu. Zgodne z konwencją macOS (jasny/ciemny motyw dopasowywany automatycznie przez system).
