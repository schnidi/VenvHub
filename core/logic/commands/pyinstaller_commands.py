#----------------------------------------
# Súbor: core/logic/commands/pyinstaller_commands.py
#----------------------------------------

import os
import shlex
from core._path import Paths
from core.logic.birth_certificate import BirthCertificateGenerator

class PyInstallerCommandDispatcher:
    @staticmethod
    def get_build_command(
        project_path: str,  # PRIDANÝ PARAMETER
        venv_path: str,
        script_path: str,
        output_dir: str = "",
        app_name: str = "",
        icon_path: str = "",
        is_windowed: bool = False,
        is_onefile: bool = False,
        add_data_list: list = None,
        hidden_imports: list = None,
        exclude_modules: list = None,
        clean_build: bool = True,
        uac_admin: bool = False,
        log_level: str = "INFO",
        custom_args: str = "",
        birth_cert_relative_path: str = ""
    ) -> list[str]:
        
        if not script_path or not project_path:
            return []

        python_exe = Paths.get_venv_python_exe_path(venv_path)
        cmd = [python_exe, "-m", "PyInstaller"]

        if is_onefile:
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")
        if is_windowed:
            cmd.append("--noconsole")
        if clean_build:
            cmd.append("--clean")
        if app_name.strip():
            cmd.extend(["--name", app_name.strip()])
        if icon_path.strip() and os.path.exists(icon_path.strip()):
            cmd.extend(["--icon", icon_path.strip()])
            
        # Zjednodušené smerovanie výstupov, defaultne do projektu
        dist_path = os.path.join(output_dir.strip(), "dist") if output_dir.strip() else os.path.join(project_path, "dist")
        build_path = os.path.join(output_dir.strip(), "build") if output_dir.strip() else os.path.join(project_path, "build")
        spec_path = output_dir.strip() if output_dir.strip() else project_path
        
        cmd.extend(["--distpath", dist_path])
        cmd.extend(["--workpath", build_path])
        cmd.extend(["--specpath", spec_path])
            
        if uac_admin:
            cmd.append("--uac-admin")
        if log_level:
            cmd.extend(["--log-level", log_level])

        # --- ZJEDNODUŠENÁ A OPRAVENÁ LOGIKA PRE RODNÝ LIST ---
        if birth_cert_relative_path:
            try:
                # Spojíme cestu projektu s relatívnou cestou z UI
                abs_cert_dir = os.path.join(project_path, birth_cert_relative_path)

                cert_path = BirthCertificateGenerator.create_app_certificate(
                    project_name=os.path.basename(project_path),
                    venv_path=venv_path,
                    script_name=script_path,
                    output_dir=abs_cert_dir
                )
                
                if cert_path:
                    if add_data_list is None:
                        add_data_list = []
                    # Pridáme ho do zoznamu pre `--add-data`
                    add_data_list.append((cert_path, birth_cert_relative_path))
            except Exception as e:
                print(f"CHYBA pri spracovaní rodného listu: {e}")
        # --- KONIEC OPRAVY ---

        if add_data_list:
            sep = os.pathsep 
            for src, dest in add_data_list:
                cmd.extend(["--add-data", f"{src}{sep}{dest}"])
        if hidden_imports:
            for imp in hidden_imports:
                if imp.strip():
                    cmd.extend(["--hidden-import", imp.strip()])
        if exclude_modules:
            for exc in exclude_modules:
                if exc.strip():
                    cmd.extend(["--exclude-module", exc.strip()])
        if custom_args.strip():
            cmd.extend(shlex.split(custom_args.strip()))
            
        cmd.append(script_path)
        return cmd

    @staticmethod
    def get_preview_string(cmd_list: list[str]) -> str:
        if not cmd_list or len(cmd_list) < 3:
            return ""
        # Použijeme jednoduché shlex.join pre korektné zobrazenie v preview
        # Najprv oddelíme pyinstaller.exe
        base_cmd = "pyinstaller" # Na zobrazenie to stačí
        args_part = cmd_list[3:] # Zoberieme len argumenty
        
        # shlex.join to pekne pospája s úvodzovkami, kde treba
        return f'<span style="color:#007acc; font-weight:bold;">{base_cmd}</span> <span style="color:#d4d4d4;">{shlex.join(args_part)}</span>'