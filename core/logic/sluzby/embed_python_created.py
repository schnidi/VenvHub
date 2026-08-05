import os
import re
import subprocess

class EmbedPythonCreated:
    """
    Služba pre prácu so špecifikami Embed / Virtualenv prostredí.
    (Zisťovanie verzie, oprava .pth, overovanie funkčnosti PIP).
    """

    @staticmethod
    def get_python_version_short(python_exe: str) -> str:
        try:
            res = subprocess.run([python_exe, "--version"], capture_output=True, text=True, creationflags=0x08000000)
            version_str = res.stdout.strip() or res.stderr.strip()
            match = re.search(r"Python (\d+)\.(\d+)", version_str)
            if match:
                return f"{match.group(1)}{match.group(2)}"
        except Exception:
            pass
        return "312"

    @staticmethod
    def fix_pth_file(venv_path: str, python_exe: str) -> None:
        ver_short = EmbedPythonCreated.get_python_version_short(python_exe)
        pth_filename = f"python{ver_short}._pth"
        scripts_dir = os.path.join(venv_path, "Scripts")
        pth_path = os.path.join(scripts_dir, pth_filename)

        if not os.path.exists(pth_path):
            try:
                content = (
                    f"python{ver_short}.zip\n"
                    ".\n"
                    "..\n"
                    "..\\Lib\\site-packages\n"
                    "import site\n"
                )
                with open(pth_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass

    @staticmethod
    def verify_pip_functional(venv_path: str) -> bool:
        pip_exe = os.path.join(venv_path, "Scripts", "pip.exe")
        if not os.path.exists(pip_exe):
            return False
        try:
            res = subprocess.run([pip_exe, "--version"], capture_output=True, text=True, creationflags=0x08000000)
            return res.returncode == 0
        except Exception:
            return False