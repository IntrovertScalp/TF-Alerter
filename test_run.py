#!/usr/bin/env python3
import sys
import traceback

try:
    print("[TEST] Starting application...", flush=True)
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    import config
    from main import MainWindow

    print("[TEST] Imports successful", flush=True)

    app = QApplication(sys.argv)
    print("[TEST] QApplication created", flush=True)

    app.setWindowIcon(QIcon(config.LOGO_PATH))
    print("[TEST] App icon set", flush=True)

    window = MainWindow()
    print("[TEST] MainWindow created", flush=True)

    window.show()
    print("[TEST] Window.show() called", flush=True)

    print("[TEST] Starting event loop...", flush=True)
    sys.exit(app.exec())

except Exception as e:
    print(f"[ERROR] Exception occurred: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
