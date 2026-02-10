#!/usr/bin/env python3
"""
TF-Alerter Launcher - Безопасный запуск main.py
Защита от бесконечного цикла процессов
"""

import sys
import subprocess
import os
import runpy
from pathlib import Path
import time


def get_script_dir():
    """Определяем директорию где находится этот скрипт/exe"""
    if getattr(sys, "frozen", False):
        # Запуск из PyInstaller exe
        return Path(sys.argv[0]).parent.resolve()
    else:
        # Запуск обычного скрипта
        return Path(__file__).parent.resolve()


def is_already_running():
    """Проверяем что TF-Alerter еще не запущен"""
    try:
        import psutil

        current_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Ищем другие TF-Alerter процессы
                if proc.pid != current_pid:
                    if proc.name() == "TF-Alerter.exe":
                        return True
                    # Также проверяем по main.py если это Python процесс
                    cmdline = proc.cmdline()
                    if cmdline and "main.py" in str(cmdline):
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        # psutil не установлен, пропускаем эту проверку
        pass
    return False


if __name__ == "__main__":
    try:
        script_dir = get_script_dir()
        main_script = script_dir / "main.py"

        # ЗАЩИТА 1: main.py должен существовать
        if not main_script.exists():
            print(f"ОШИБКА: main.py не найден в {script_dir}")
            print(f"Script dir: {script_dir}")
            print(f"Files in dir: {list(script_dir.glob('*.py'))[:5]}")
            sys.exit(1)

        # ЗАЩИТА 2: Ищем Python интерпретатор
        python_exe = None

        # Попытка 1: .venv в текущей папке (развитие)
        venv_python = script_dir / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            python_exe = str(venv_python)
            print(f"Found venv Python: {python_exe}")

        # Попытка 2: Если это frozen exe, попробовать использовать встроенный Python
        if not python_exe and getattr(sys, "frozen", False):
            # При замораживании exe PyInstaller включает python.exe внутри распакованной папки
            # Попробуем найти его
            base_dir = Path(sys.executable).parent
            embedded_python = base_dir / "python.exe"
            if embedded_python.exists():
                python_exe = str(embedded_python)
                print(f"Found embedded Python: {python_exe}")

        # Попытка 3: Системный Python (если это не exe)
        if not python_exe:
            sys_python = sys.executable
            if (
                sys_python.endswith("python.exe")
                and "TF-Alerter.exe" not in sys_python
                and "launcher.exe" not in sys_python
            ):
                python_exe = sys_python
                print(f"Using system Python: {python_exe}")

        if not python_exe:
            print("\n" + "=" * 60)
            print("ОШИБКА: Python не найден!")
            print("=" * 60)
            print(f"sys.executable: {sys.executable}")
            print(f"venv exists: {venv_python.exists()}")
            print(f"is_frozen: {getattr(sys, 'frozen', False)}")
            print("\nРЕШЕНИЕ:")
            print("1. Установите Python с https://www.python.org/downloads/")
            print("2. Во время установки выберите 'Add Python to PATH'")
            print("3. После этого запустите TF-Alerter.exe снова")
            print("\nИЛИ используйте исходный код:")
            print("- Установите Python")
            print("- Выполните: pip install -r requirements.txt")
            print("- Запустите: python main.py")
            print("=" * 60 + "\n")
            sys.exit(1)

        # ЗАЩИТА 3: Убедимся что это точно Python, а не exe
        if python_exe.lower().endswith(".exe"):
            if "python" not in python_exe.lower():
                print(f"ОШИБКА: Неверный интерпретатор: {python_exe}")
                sys.exit(1)

        # Подготовка окружения
        env = os.environ.copy()
        env["TFALER_HOME"] = str(script_dir)
        env["PYTHONPATH"] = str(script_dir)

        # ЗАЩИТА 4: No infinite loop - используем абсолютный путь main.py
        main_script_str = str(main_script.resolve())
        if not main_script_str.lower().endswith("main.py"):
            print(f"ОШИБКА: Неверный путь скрипта: {main_script_str}")
            sys.exit(1)

        # ЗАЩИТА 5: Запускаем с Job Group на Windows (все процессы в одной группе)
        kwargs = {
            "cwd": str(script_dir),
            "env": env,
        }

        if sys.platform == "win32":
            # CREATE_NEW_PROCESS_GROUP позволяет завершить все дочерние процессы вместе
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        # Запускаем main.py
        process = subprocess.Popen([python_exe, main_script_str], **kwargs)

        # ГЛАВНОЕ: Ждем завершения процесса и выходим
        exit_code = process.wait()

        # Критически важно: выходим сразу после завершения main.py
        sys.exit(exit_code)

    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА В LAUNCHER: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
