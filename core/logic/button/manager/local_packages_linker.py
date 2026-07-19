#----------------------------------------------------
# Súbor: core/logic/button/manager/local_packages_linker.py
#----------------------------------------------------

import os
import json
import subprocess
from collections import deque
from PyQt6.QtWidgets import QMessageBox, QApplication

from core.logic.language_manager import LanguageManager
from core._path import Paths
from core.logic.vs_code_json import VSCodeIntegration
from core.logic.commands.command_factory import PackageManagerFactory

class LocalPackagesLinker:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.core = parent_window.core
        self.venv_path = parent_window.venv_path
        self.log_callback = parent_window.log

    def apply_changes(self, selected_items_data):
        self.log_callback(LanguageManager.get("msg_saving_changes_deps", "\n--- Ukladám zmeny a analyzujem závislosti ---"))
        
        # 1. Zablokujeme UI, aby užívateľ nezavrel okno počas inštalácie
        self._set_ui_enabled(False)

        try:
            # NORMALIZÁCIA: použijeme názov adresára ako meno balíka
            for item in selected_items_data:
                item['name'] = os.path.basename(item['path'])

            all_packages_to_link, pip_dependencies = self._resolve_dependencies(selected_items_data)
            if all_packages_to_link is None:
                return False

            # 2. Vytvorenie tichého prepojenia (Import Hook) namiesto Junctions
            added_count, removed_count = self._manage_hook_files(all_packages_to_link)

            # 3. Bezpečné synchrónne stiahnutie závislostí (UV / PIP)
            if pip_dependencies:
                self.log_callback(LanguageManager.get("msg_detected_ext_deps", "Detekované externé závislosti: {0}").format(', '.join(pip_dependencies)))
                self._install_dependencies_safely(pip_dependencies)

            # 4. Aktualizácia VS Code (Pošleme priamo skutočné zdrojové cesty balíčkov pre Pylance)
            project_path = Paths.get_project_path(self.core.projects_root, self.core.active_project)
            
            target_paths = [pkg_data['path'] for pkg_data in all_packages_to_link.values()]
            
            try:
                VSCodeIntegration.sync_local_packages(project_path, target_paths, self.core.local_packages_root)
                VSCodeIntegration.sync_vscode_tasks_and_keybindings(project_path, target_paths, self.core.local_packages_root, self.log_callback)
            except Exception as e:
                self.log_callback(LanguageManager.get("msg_vscode_err", "Chyba VS Code: {0}").format(e))

            # 5. Prehľadné zhrnutie na konci
            if added_count == 0 and removed_count == 0:
                self.log_callback(LanguageManager.get("msg_no_changes_local_pkgs", "ℹ️ Neboli vykonané žiadne zmeny, stav je aktuálny."))
            else:
                self.log_callback(LanguageManager.get("msg_changes_saved_local_pkgs", "✅ Zmeny úspešne uložené (Pridané: {0}, Odstránené: {1}).").format(added_count, removed_count))

            self.log_callback(LanguageManager.get("msg_done_simple", "--- Hotovo ---"))
            return True

        finally:
            self._set_ui_enabled(True)

    def _set_ui_enabled(self, enabled):
        if hasattr(self.parent, 'btn_apply'): self.parent.btn_apply.setEnabled(enabled)
        if hasattr(self.parent, 'btn_refresh'): self.parent.btn_refresh.setEnabled(enabled)
        if hasattr(self.parent, 'table_packages'): self.parent.table_packages.setEnabled(enabled)
        QApplication.processEvents()

    def _resolve_dependencies(self, selected_items_data):
        all_to_link = {item['name']: item for item in selected_items_data}
        pip_deps = set()
        queue = deque([item['name'] for item in selected_items_data])

        while queue:
            pkg_name = queue.popleft()
            pkg_data = all_to_link.get(pkg_name)
            if not pkg_data:
                continue
            meta_path = os.path.join(pkg_data['path'], "local_meta.json")
            if not os.path.exists(meta_path):
                continue
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                for pip_pkg in meta.get("requires_pip", []):
                    pip_deps.add(pip_pkg)
                for local_dep_name in meta.get("requires_local", []):
                    found = False
                    for existing_name, existing_data in all_to_link.items():
                        if existing_name == local_dep_name or existing_data['name'] == local_dep_name:
                            found = True
                            break
                    if not found:
                        dep_path = os.path.join(self.core.local_packages_root, local_dep_name)
                        if not os.path.isdir(dep_path):
                            msg = LanguageManager.get("msg_missing_local_dep", "Chýba lokálna závislosť: {0} pre {1}").format(local_dep_name, pkg_name)
                            self.log_callback(msg)
                            QMessageBox.critical(self.parent, LanguageManager.get("title_error", "Chyba"), msg)
                            return None, None
                        new_name = os.path.basename(dep_path)
                        all_to_link[new_name] = {'name': new_name, 'path': dep_path}
                        queue.append(new_name)
            except (json.JSONDecodeError, OSError, IOError) as e:
                self.log_callback(LanguageManager.get("msg_metadata_err", "Chyba v metadátach {0}: {1}").format(pkg_name, e))
        return all_to_link, list(pip_deps)

    def _manage_hook_files(self, packages_dict):
        """
        Vytvorí alebo zmaže .json, .py a .pth súbory v site-packages
        namiesto vytvárania NTFS Junctions, čím kompletne eliminuje UAC okná.
        """
        site_folder = "Lib" if os.name == 'nt' else "lib"
        site_packages = os.path.join(self.venv_path, site_folder, "site-packages")
        os.makedirs(site_packages, exist_ok=True)

        json_file = os.path.join(site_packages, "venvhub.json")
        py_file = os.path.join(site_packages, "venvhub_bootstrap.py")
        pth_file = os.path.join(site_packages, "venvhub_bootstrap.pth")
        
        # Starý Junctions marker, upraceme ho, ak náhodou existuje
        old_marker = os.path.join(site_packages, ".venvhub_linked")
        if os.path.exists(old_marker):
            try: os.remove(old_marker)
            except: pass

        existing_keys = set()
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    existing_keys = set(json.load(f).keys())
            except Exception:
                pass

        wanted_keys = set(packages_dict.keys())
        added_count = len(wanted_keys - existing_keys)
        removed_count = len(existing_keys - wanted_keys)

        # Ak používateľ neoznačil žiadny balíček, zmažeme hook súbory
        if not packages_dict:
            for filepath in [json_file, py_file, pth_file]:
                if os.path.exists(filepath):
                    try: os.remove(filepath)
                    except: pass
            return added_count, removed_count

        # 1. Zápis venvhub.json (Mapovanie ciest)
        mapping = {name: os.path.normpath(data['path']) for name, data in packages_dict.items()}
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log_callback(f"Chyba pri zápise venvhub.json: {e}")

        # 2. Zápis venvhub_bootstrap.py (Samotný import hook)
        bootstrap_code = """import sys
import os
import json
import importlib.util

class VenvHubFinder:
    def __init__(self, mapping):
        self.mapping = mapping

    def find_spec(self, fullname, path, target=None):
        parts = fullname.split('.')
        root_name = parts[0]

        if root_name in self.mapping:
            base_path = self.mapping[root_name]

            if len(parts) == 1:
                init_py = os.path.join(base_path, "__init__.py")
                if os.path.exists(init_py):
                    return importlib.util.spec_from_file_location(
                        fullname, 
                        init_py, 
                        submodule_search_locations=[base_path]
                    )
            else:
                sub_path = os.path.join(base_path, *parts[1:])
                py_file = sub_path + ".py"
                if os.path.exists(py_file):
                    return importlib.util.spec_from_file_location(fullname, py_file)
                sub_init = os.path.join(sub_path, "__init__.py")
                if os.path.exists(sub_init):
                    return importlib.util.spec_from_file_location(
                        fullname, 
                        sub_init, 
                        submodule_search_locations=[sub_path]
                    )
        return None

current_dir = os.path.dirname(__file__)
json_path = os.path.join(current_dir, "venvhub.json")

if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        sys.meta_path.insert(0, VenvHubFinder(mapping))
    except Exception:
        pass
"""
        try:
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(bootstrap_code)
        except Exception as e:
            self.log_callback(f"Chyba pri zápise venvhub_bootstrap.py: {e}")

        # 3. Zápis venvhub_bootstrap.pth (Trigger pre Python)
        try:
            with open(pth_file, "w", encoding="utf-8") as f:
                f.write("import venvhub_bootstrap\n")
        except Exception as e:
            self.log_callback(f"Chyba pri zápise venvhub_bootstrap.pth: {e}")

        return added_count, removed_count

    def _install_dependencies_safely(self, dependencies: list):
        try:
            manager_type = getattr(self.core, 'package_manager', 'pip')
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, self.venv_path)
            cmd = dispatcher.get("install_multiple_exact", packages=dependencies)
            
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                creationflags=CREATE_NO_WINDOW
            )
            
            for line in iter(process.stdout.readline, ''):
                clean_line = line.strip()
                if clean_line:
                    self.log_callback(f"  {clean_line}")
                    QApplication.processEvents()
                    
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            self.log_callback(LanguageManager.get("msg_dep_install_err", "Chyba inštalácie závislostí: {0}").format(e))
            return False