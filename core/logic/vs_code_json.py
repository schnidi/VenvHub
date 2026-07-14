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
    def sync_vscode_tasks_and_keybindings(project_path: str, local_packages_root: str, log_callback=None):
        def log(msg):
            if log_callback:
                log_callback(msg)
            else:
                print(msg)

        log(LanguageManager.get("vscode_sync_start", "\n[VSCODE TASKS SYNC] Spúšťam synchronizáciu..."))
        log(f"  project_path = {project_path}")
        log(f"  local_packages_root = {local_packages_root}")

        if not project_path:
            log(LanguageManager.get("vscode_sync_err_no_project", "❌ CHYBA: project_path je prázdny"))
            return
        if not os.path.exists(project_path):
            log(LanguageManager.get("vscode_sync_err_project_missing", "❌ CHYBA: project_path neexistuje: {path}").format(path=project_path))
            return
        if not local_packages_root:
            log(LanguageManager.get("vscode_sync_err_no_local_root", "❌ CHYBA: local_packages_root je prázdny"))
            return
        if not os.path.exists(local_packages_root):
            log(LanguageManager.get("vscode_sync_err_local_root_missing", "❌ CHYBA: local_packages_root neexistuje: {path}").format(path=local_packages_root))
            return

        vscode_dir = os.path.join(project_path, ".vscode")
        os.makedirs(vscode_dir, exist_ok=True)
        log(LanguageManager.get("vscode_sync_dir_ok", "✅ .vscode priečinok: {dir}").format(dir=vscode_dir))

        tasks_file = os.path.join(vscode_dir, "tasks.json")
        keybindings_file = os.path.join(vscode_dir, "keybindings.json")

        existing_tasks = VSCodeIntegration._load_json(tasks_file)
        existing_keybindings = VSCodeIntegration._load_json(keybindings_file)

        if existing_tasks is None:
            existing_tasks = {"version": "2.0.0", "tasks": []}
            log(LanguageManager.get("vscode_sync_tasks_new", "ℹ️ tasks.json neexistuje, vytvorím nový."))
        else:
            log(LanguageManager.get("vscode_sync_tasks_exist", "ℹ️ tasks.json už existuje, obsahuje {count} úloh.").format(count=len(existing_tasks.get('tasks', []))))
        if existing_keybindings is None:
            existing_keybindings = []
            log(LanguageManager.get("vscode_sync_keys_new", "ℹ️ keybindings.json neexistuje, vytvorím nový."))
        else:
            log(LanguageManager.get("vscode_sync_keys_exist", "ℹ️ keybindings.json už existuje, obsahuje {count} skratiek.").format(count=len(existing_keybindings)))

        all_new_tasks = []
        all_new_keybindings = []

        try:
            items = os.listdir(local_packages_root)
            log(LanguageManager.get("vscode_sync_scanning", "📂 Skenujem {count} položiek v local_packages_root...").format(count=len(items)))
            for pkg_name in items:
                pkg_dir = os.path.join(local_packages_root, pkg_name)
                if not os.path.isdir(pkg_dir):
                    log(LanguageManager.get("vscode_sync_skip_not_dir", "  ⏭️ Preskakujem {name} (nie je priečinok)").format(name=pkg_name))
                    continue
                meta_path = os.path.join(pkg_dir, "local_meta.json")
                if not os.path.exists(meta_path):
                    log(LanguageManager.get("vscode_sync_skip_no_meta", "  ⏭️ Preskakujem {name} (chýba local_meta.json)").format(name=pkg_name))
                    continue

                log(LanguageManager.get("vscode_sync_processing", "  📄 Spracúvam {name} -> {path}").format(name=pkg_name, path=meta_path))
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    vscode_int = meta.get("vscode_integration", {})
                    tasks = vscode_int.get("tasks", [])
                    keybindings = vscode_int.get("keybindings", [])

                    log(LanguageManager.get("vscode_sync_found_items", "     Nájdených {tasks} úloh a {keys} skratiek.").format(tasks=len(tasks), keys=len(keybindings)))

                    for task in tasks:
                        label = task.get("label")
                        if label and not any(t.get("label") == label for t in existing_tasks.get("tasks", [])):
                            all_new_tasks.append(task)
                            log(LanguageManager.get("vscode_sync_new_task", "       ✅ Nová úloha: {label}").format(label=label))
                        else:
                            log(LanguageManager.get("vscode_sync_skip_task", "       ⏭️ Úloha {label} už existuje, preskakujem.").format(label=label))

                    for kb in keybindings:
                        key = kb.get("key")
                        command = kb.get("command")
                        if key and command and not any(
                            k.get("key") == key and k.get("command") == command
                            for k in existing_keybindings
                        ):
                            all_new_keybindings.append(kb)
                            log(LanguageManager.get("vscode_sync_new_key", "       ✅ Nová skratka: {key} -> {command}").format(key=key, command=command))
                        else:
                            log(LanguageManager.get("vscode_sync_skip_key", "       ⏭️ Skratka {key} ({command}) už existuje, preskakujem.").format(key=key, command=command))

                except Exception as e:
                    log(LanguageManager.get("vscode_sync_err_read", "       ❌ Chyba pri čítaní {path}: {error}").format(path=meta_path, error=e))

            modified = False
            if all_new_tasks:
                existing_tasks.setdefault("tasks", []).extend(all_new_tasks)
                modified = True
                log(LanguageManager.get("vscode_sync_added_tasks", "📝 Pridaných {count} nových úloh do tasks.json").format(count=len(all_new_tasks)))
            if all_new_keybindings:
                existing_keybindings.extend(all_new_keybindings)
                modified = True
                log(LanguageManager.get("vscode_sync_added_keys", "📝 Pridaných {count} nových skratiek do keybindings.json").format(count=len(all_new_keybindings)))

            if modified:
                success_tasks = VSCodeIntegration._save_json(tasks_file, existing_tasks)
                success_keys = VSCodeIntegration._save_json(keybindings_file, existing_keybindings)
                if success_tasks:
                    log(LanguageManager.get("vscode_sync_save_tasks_ok", "✅ tasks.json uložený: {file}").format(file=tasks_file))
                else:
                    log(LanguageManager.get("vscode_sync_save_tasks_err", "❌ CHYBA pri ukladaní tasks.json"))
                if success_keys:
                    log(LanguageManager.get("vscode_sync_save_keys_ok", "✅ keybindings.json uložený: {file}").format(file=keybindings_file))
                else:
                    log(LanguageManager.get("vscode_sync_save_keys_err", "❌ CHYBA pri ukladaní keybindings.json"))
            else:
                log(LanguageManager.get("vscode_sync_no_changes", "ℹ️ Žiadne nové položky na pridanie, súbory zostávajú nezmenené."))

        except Exception as e:
            log(LanguageManager.get("vscode_sync_err_critical", "❌ KRITICKÁ CHYBA: {error}").format(error=e))

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