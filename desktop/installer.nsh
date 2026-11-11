; The uninstaller asks whether to remove the studio's Linux and the data in it (specs/016 FR-005).
; The default keeps them, and an update (a newer installer over this one) never asks.
!macro customUnInstall
  ${ifNot} ${isUpdated}
    MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "Also remove the studio's Linux (ClaudeUtube) with your films, channels and accounts?$\r$\n$\r$\nChoose No to keep them for a later install." /SD IDNO IDNO cu_keep
      nsExec::ExecToLog 'wsl.exe --unregister ClaudeUtube'
      RMDir /r "$LOCALAPPDATA\ClaudeUtube"
    cu_keep:
  ${endIf}
!macroend
