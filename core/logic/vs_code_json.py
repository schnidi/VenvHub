#----------------------------------------
# Súbor: core/logic/vs_code_json.py (VERZIA S DETAILNÝM LOGOVANÍM)
#----------------------------------------

import os
import json
from core.logic.language_manager import LanguageManager

class VSCodeIntegration:
    # ========== PÔVODNÉ METÓDY (ZACHOVANÉ) ==========
    @staticmethod
    def initialize_project_settings(project_path: str, venv_path: str):
        if not project_path or not venv_path:
            return
        vscode_folder = os.path.join(project_path, ".vscode")
        settings_file = os.path.join(vscode_folder, "settings.json")
        try:
            os.makedirs(vscode_folder, exist_ok=True)
        except OSError:
            return
        vscode_config = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        vscode_config = json.loads(content)
            except (json.JSONDecodeError, OSError):
                vscode_config = {}
        if "python.defaultInterpreterPath" in vscode_config:
            return
        python_exe = os.path.join(venv_path, "Scripts", "python.exe").replace("\\", "/")
        vscode_config["python.defaultInterpreterPath"] = python_exe
        vscode_config["python.terminal.activateEnvironment"] = True
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(vscode_config, f, indent=4)
        except OSError:
            pass

    @staticmethod
    def set_default_interpreter(project_path: str, venv_path: str):
        if not project_path or not venv_path:
            return
        vscode_folder = os.path.join(project_path, ".vscode")
        settings_file = os.path.join(vscode_folder, "settings.json")
        try:
            os.makedirs(vscode_folder, exist_ok=True)
        except OSError:
            return
        python_exe = os.path.join(venv_path, "Scripts", "python.exe").replace("\\", "/")
        vscode_config = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        vscode_config = json.loads(content)
            except (json.JSONDecodeError, OSError):
                pass
        vscode_config["python.defaultInterpreterPath"] = python_exe
        vscode_config["python.terminal.activateEnvironment"] = True
        for key in ["python.venvPath", "python.envFile"]:
            if key in vscode_config:
                del vscode_config[key]
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(vscode_config, f, indent=4)
        except OSError:
            pass

    @staticmethod
    def remove_vscode_sync(project_path: str):
        if not project_path or not os.path.exists(project_path):
            return
        vscode_folder = os.path.join(project_path, ".vscode")
        settings_file = os.path.join(vscode_folder, "settings.json")
        if not os.path.exists(settings_file):
            return
        vscode_config = {}
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    vscode_config = json.loads(content)
        except (json.JSONDecodeError, OSError):
            pass
        keys_to_remove = ["python.defaultInterpreterPath", "python.terminal.activateEnvironment"]
        modified = False
        for key in keys_to_remove:
            if key in vscode_config:
                del vscode_config[key]
                modified = True
        if modified:
            if not vscode_config:
                try:
                    os.remove(settings_file)
                    if not os.listdir(vscode_folder):
                        os.rmdir(vscode_folder)
                except OSError:
                    pass
            else:
                try:
                    with open(settings_file, "w", encoding="utf-8") as f:
                        json.dump(vscode_config, f, indent=4)
                except OSError:
                    pass

    @staticmethod
    def repair_portable_path(project_path: str, new_venv_path: str, local_packages_root: str = ""):
        if not project_path or not new_venv_path:
            return
        settings_file = os.path.join(project_path, ".vscode", "settings.json")
        if not os.path.exists(settings_file):
            return
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    return
                vscode_config = json.loads(content)
            old_py_path = vscode_config.get("python.defaultInterpreterPath")
            if not old_py_path:
                return
            modified = False
            new_py_path = os.path.join(new_venv_path, "Scripts", "python.exe").replace("\\", "/")
            if old_py_path.lower() != new_py_path.lower():
                vscode_config["python.defaultInterpreterPath"] = new_py_path
                modified = True
            if local_packages_root and "python.analysis.extraPaths" in vscode_config:
                old_extra_paths = vscode_config["python.analysis.extraPaths"]
                new_extra_paths = []
                for path in old_extra_paths:
                    if "site-packages" in path:
                        parts = path.replace("\\", "/").split("/site-packages/")
                        if len(parts) == 2:
                            site_folder = "Lib" if os.name == 'nt' else "lib"
                            new_site_path = os.path.join(new_venv_path, site_folder, "site-packages", parts[1]).replace("\\", "/")
                            new_extra_paths.append(new_site_path)
                            if new_site_path != path:
                                modified = True
                            continue
                    new_extra_paths.append(path)
                vscode_config["python.analysis.extraPaths"] = new_extra_paths
            if modified:
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(vscode_config, f, indent=4)
        except Exception:
            pass

    @staticmethod
    def sync_local_packages(project_path: str, selected_paths: list[str], local_packages_root: str):
        if not project_path:
            return
        vscode_folder = os.path.join(project_path, ".vscode")
        settings_file = os.path.join(vscode_folder, "settings.json")
        try:
            os.makedirs(vscode_folder, exist_ok=True)
        except OSError:
            return
        vscode_config = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        vscode_config = json.loads(content)
            except (json.JSONDecodeError, OSError):
                pass
        extra_paths = vscode_config.get("python.analysis.extraPaths", [])
        if not isinstance(extra_paths, list):
            extra_paths = []
        if local_packages_root and os.path.exists(local_packages_root):
            norm_root = os.path.normpath(local_packages_root).replace("\\", "/").lower()
            extra_paths = [
                p for p in extra_paths
                if not os.path.normpath(p).replace("\\", "/").lower().startswith(norm_root)
            ]
        for p in selected_paths:
            clean_p = os.path.normpath(p).replace("\\", "/")
            if clean_p not in extra_paths:
                extra_paths.append(clean_p)
        if extra_paths:
            vscode_config["python.analysis.extraPaths"] = extra_paths
        else:
            if "python.analysis.extraPaths" in vscode_config:
                del vscode_config["python.analysis.extraPaths"]
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(vscode_config, f, indent=4)
        except OSError:
            pass

    # ==========================================================
    # NOVÉ METÓDY PRE TASKS A KEYBINDINGS Z LOCAL_META.JSON
    # S DETAILNÝM LOGOVANÍM
    # ==========================================================

    @staticmethod
    def sync_vscode_tasks_and_keybindings(project_path: str, selected_paths: list[str], local_packages_root: str, log_callback=None):
        def log(msg):
            if log_callback: log_callback(msg)
            else: print(msg)

        log(LanguageManager.get("vscode_sync_start", "\n[VSCODE TASKS SYNC] Spúšťam synchronizáciu (Brutal Check)..."))

        if not project_path or not os.path.exists(project_path):
            log(LanguageManager.get("vscode_sync_err_no_project", "❌ CHYBA: project_path neexistuje."))
            return

        vscode_dir = os.path.join(project_path, ".vscode")
        os.makedirs(vscode_dir, exist_ok=True)

        # 1. Definícia ciest k súborom vo VS Code
        tasks_file = os.path.join(vscode_dir, "tasks.json")
        keybindings_file = os.path.join(vscode_dir, "keybindings.json")
        tracker_file = os.path.join(vscode_dir, "venvhub_tracker.json") # Naša "účtenka"

        # 2. Načítanie aktuálneho stavu (alebo vytvorenie prázdnych štruktúr)
        existing_tasks = VSCodeIntegration._load_json(tasks_file) or {"version": "2.0.0", "tasks": []}
        existing_keybindings = VSCodeIntegration._load_json(keybindings_file) or []
        tracker = VSCodeIntegration._load_json(tracker_file) or {}

        # 3. IDENTIFIKÁCIA ZMIEN (Staré vs. Nové)
        new_package_names = [os.path.basename(p) for p in selected_paths]
        old_package_names = list(tracker.keys())

        # Čo bolo v účtenke, ale už nie je zaškrtnuté (alebo sme prepli Venv)
        packages_to_remove = [pkg for pkg in old_package_names if pkg not in new_package_names]
        
        modified_tasks = False
        modified_keys = False

        # =====================================================================
        # FÁZA 1: MAZANIE (Upratovanie odškrtnutých / zmazaných)
        # =====================================================================
        if packages_to_remove:
            log(LanguageManager.get("vscode_sync_removing", "🧹 Odstraňujem integráciu pre {0} deaktivovaných balíčkov...").format(len(packages_to_remove)))

        for pkg_name in packages_to_remove:
            tasks_to_remove = []
            keys_to_remove = []

            pkg_dir = os.path.join(local_packages_root, pkg_name)
            meta_path = os.path.join(pkg_dir, "local_meta.json")
            read_from_disk = False

            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        vscode_int = meta.get("vscode_integration", {})
                        tasks_to_remove = [t.get("label") for t in vscode_int.get("tasks", []) if t.get("label")]
                        keys_to_remove = [{"key": k.get("key"), "command": k.get("command")} for k in vscode_int.get("keybindings", []) if k.get("key") and k.get("command")]
                        read_from_disk = True
                        log(LanguageManager.get("vscode_sync_read_disk", "  🗑️ Balíček '{0}' prečítaný. Mažem jeho úlohy z editora.").format(pkg_name))
                except Exception: pass

            # Záchranná brzda - Účtenka
            if not read_from_disk:
                log(LanguageManager.get("vscode_sync_use_tracker", "  ⚠️ Balíček '{0}' zmazaný z disku! Používam záchrannú účtenku.").format(pkg_name))
                tracker_data = tracker.get(pkg_name, {})
                tasks_to_remove = tracker_data.get("tasks", [])
                keys_to_remove = tracker_data.get("keybindings", [])

            # Výkonná moc mazania
            if tasks_to_remove:
                original_len = len(existing_tasks.get("tasks", []))
                existing_tasks["tasks"] = [t for t in existing_tasks.get("tasks", []) if t.get("label") not in tasks_to_remove]
                if len(existing_tasks["tasks"]) != original_len:
                    modified_tasks = True

            if keys_to_remove:
                original_len = len(existing_keybindings)
                existing_keybindings = [
                    k for k in existing_keybindings 
                    if not any(rem.get("key") == k.get("key") and rem.get("command") == k.get("command") for rem in keys_to_remove)
                ]
                if len(existing_keybindings) != original_len:
                    modified_keys = True

            # Vyškrtnutie z účtenky
            del tracker[pkg_name]


        # =====================================================================
        # FÁZA 2: INJEKCIA (Pridávanie nových / aktívnych)
        # =====================================================================
        for pkg_dir in selected_paths:
            pkg_name = os.path.basename(pkg_dir)
            meta_path = os.path.join(pkg_dir, "local_meta.json")
            
            if not os.path.exists(meta_path): continue

            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    
                vscode_int = meta.get("vscode_integration", {})
                tasks = vscode_int.get("tasks", [])
                keybindings = vscode_int.get("keybindings", [])

                injected_tasks = []
                injected_keys = []

                for task in tasks:
                    label = task.get("label")
                    if label and not any(t.get("label") == label for t in existing_tasks.get("tasks", [])):
                        existing_tasks.setdefault("tasks", []).append(task)
                        modified_tasks = True
                        injected_tasks.append(label)

                for kb in keybindings:
                    key = kb.get("key")
                    command = kb.get("command")
                    if key and command and not any(k.get("key") == key and k.get("command") == command for k in existing_keybindings):
                        existing_keybindings.append(kb)
                        modified_keys = True
                        injected_keys.append({"key": key, "command": command})

                # Zápis do účtenky
                if injected_tasks or injected_keys or pkg_name in tracker:
                    tracker[pkg_name] = {
                        "tasks": injected_tasks,
                        "keybindings": injected_keys
                    }

            except Exception as e:
                log(LanguageManager.get("vscode_sync_err_read", "       ❌ Chyba pri čítaní {0}: {1}").format(meta_path, e))


        # =====================================================================
        # FÁZA 3: UKLADANIE A UPRATOVANIE PRÁZDNYCH SÚBOROV Z DISKU
        # =====================================================================
        
        # 3.1: Tasks.json
        if not existing_tasks.get("tasks"): 
            if os.path.exists(tasks_file):
                os.remove(tasks_file)
                log(LanguageManager.get("vscode_sync_del_tasks", "🗑️ tasks.json zostal prázdny, zmazal som ho z disku."))
        elif modified_tasks:
            VSCodeIntegration._save_json(tasks_file, existing_tasks)
            log(LanguageManager.get("vscode_sync_save_tasks_ok", "✅ tasks.json úspešne uložený."))

        # 3.2: Keybindings.json
        if not existing_keybindings:
            if os.path.exists(keybindings_file):
                os.remove(keybindings_file)
                log(LanguageManager.get("vscode_sync_del_keys", "🗑️ keybindings.json zostal prázdny, zmazal som ho z disku."))
        elif modified_keys:
            VSCodeIntegration._save_json(keybindings_file, existing_keybindings)
            log(LanguageManager.get("vscode_sync_save_keys_ok", "✅ keybindings.json úspešne uložený."))

        # 3.3: Tracker (Účtenka)
        if not tracker:
            if os.path.exists(tracker_file):
                os.remove(tracker_file)
        else:
            VSCodeIntegration._save_json(tracker_file, tracker)

        if not modified_tasks and not modified_keys and not packages_to_remove:
            log(LanguageManager.get("vscode_sync_no_changes", "ℹ️ VS Code je už synchronizovaný, neboli potrebné žiadne zmeny."))

        log(LanguageManager.get("vscode_sync_end", "--- Synchronizácia ukončená ---"))

    @staticmethod
    def _load_json(file_path):
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(LanguageManager.get("vscode_sync_log_err_load", "[_load_json] Chyba pri načítaní {file}: {error}").format(file=file_path, error=e))
            return None

    @staticmethod
    def _save_json(file_path, data):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(LanguageManager.get("vscode_sync_log_err_save", "[_save_json] Chyba pri zápise {file}: {error}").format(file=file_path, error=e))
            return False