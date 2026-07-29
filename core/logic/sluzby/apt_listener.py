#----------------------------------------
# Súbor: core/logic/sluzby/apt_listener.py
#----------------------------------------

import os
import json
import subprocess
from core._path import Paths
from core.logic.sluzby.apt_logic import AptLogic
from core.logic.sluzby.requirements_parser import RequirementsParser
from core.logic.commands.command_factory import PackageManagerFactory
from core.logic.language_manager import LanguageManager

class AptListener:
    """
    Neviditeľný most (Interceptor), ktorý počúva na pozadí všetky akcie.
    Automaticky zapisuje manuálne inštalácie a odinštalácie do APT logiky.
    """

    @staticmethod
    def start_listening(core):
        AptListener._patch_pip_manager(core)
        AptListener._patch_pip_package_widget(core)
        AptListener._patch_pipe_install(core)
        AptListener._patch_pipe_uninstall(core)
        AptListener._patch_local_linker(core)

    @staticmethod
    def _get_editable_packages(venv_path):
        """
        Získa zoznam -e balíčkov vo forme JSON (list slovníkov) priamo z venvu.
        Vráti napr.: [{"name": "moj-balicek", "version": "0.1.0", "editable_project_location": "C:/Cesta"}]
        """
        python_exe = Paths.get_venv_python_exe_path(venv_path)
        if not os.path.exists(python_exe):
            return []

        cmd = [python_exe, "-m", "pip", "list", "--editable", "--format=json"]
        CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception:
            pass

        return []

    @staticmethod
    def _extract_packages_from_install_cmd(cmd_list):
        pkgs = []
        cmd_lower = [x.lower() for x in cmd_list]
        if "install" in cmd_lower and "-r" not in cmd_lower:
            idx = cmd_lower.index("install")
            for arg in cmd_list[idx+1:]:
                if not arg.startswith("-"):
                    clean_pkg = RequirementsParser._extract_package_name(arg)
                    if clean_pkg: 
                        pkgs.append(clean_pkg)
        return pkgs

    @staticmethod
    def _extract_packages_from_uninstall_cmd(cmd_list):
        pkgs = []
        cmd_lower = [x.lower() for x in cmd_list]
        if "uninstall" in cmd_lower:
            idx = cmd_lower.index("uninstall")
            for arg in cmd_list[idx+1:]:
                if not arg.startswith("-"):
                    clean_pkg = RequirementsParser._extract_package_name(arg)
                    if clean_pkg:
                        pkgs.append(clean_pkg)
        return pkgs

    @staticmethod
    def _is_package_required_by_others(venv_path, core, package_name):
        """
        Skontroluje, či na danom balíčku závisia iné nainštalované balíčky (reverzné závislosti)
        A TAKTIEŽ či ho nevyžaduje niektorý z prepojených Linker balíčkov.
        """
        pkg_norm = AptLogic._normalize(package_name)
        dependents = []

        # 1. Kontrola štandardných PIP závislostí
        graph = AptLogic.get_dependency_graph(venv_path, core)
        for other_pkg, requirements in graph.items():
            if other_pkg == pkg_norm:
                continue
            if pkg_norm in requirements:
                dependents.append(other_pkg)

        # 2. Kontrola VenvHub Linker závislostí (venvhub.json -> local_meta.json)
        site_folder = "Lib" if os.name == 'nt' else "lib"
        venvhub_json = os.path.join(venv_path, site_folder, "site-packages", "venvhub.json")

        if os.path.exists(venvhub_json):
            try:
                with open(venvhub_json, 'r', encoding='utf-8') as f:
                    linked_map = json.load(f)
                    
                for pkg_key, pkg_path in linked_map.items():
                    meta_path = os.path.join(pkg_path, "local_meta.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as mf:
                                meta = json.load(mf)
                                name = meta.get("name", pkg_key)
                                reqs = [AptLogic._normalize(r) for r in meta.get("requires_pip", [])]
                                
                                if pkg_norm in reqs:
                                    display_name = f"{name} (Linker)"
                                    if display_name not in dependents:
                                        dependents.append(display_name)
                        except Exception:
                            pass
            except Exception:
                pass

        return dependents

    @staticmethod
    def _get_requires_for_package(venv_path, pkg_name, manager_type="pip"):
        reqs = []
        try:
            dispatcher = PackageManagerFactory.get_dispatcher(manager_type, venv_path)
            cmd = dispatcher.get("show", package_name=pkg_name)
            
            CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            for line in res.stdout.splitlines():
                if line.startswith("Requires:"):
                    val = line.replace("Requires:", "").strip()
                    if val: 
                        reqs = [r.strip().lower() for r in val.split(",")]
        except Exception: 
            pass
        return reqs

    @staticmethod
    def _patch_pip_manager(core):
        from core.logic.pip_manager import PipManager
        orig_run_pip_task = PipManager._run_pip_task

        @staticmethod
        def patched_run_pip_task(worker, log_widget):
            if hasattr(worker, 'cmd'):
                cmd_lower = [x.lower() for x in worker.cmd]
                is_uninstall = "uninstall" in cmd_lower

                if is_uninstall:
                    pkgs_to_uninstall = AptListener._extract_packages_from_uninstall_cmd(worker.cmd)
                    for pkg in pkgs_to_uninstall:
                        deps = AptListener._is_package_required_by_others(worker.venv_path, core, pkg)
                        if deps:
                            msg = LanguageManager.get(
                                "apt_err_cannot_uninstall",
                                "❌ Nemožno odinštalovať '{0}', pretože ho vyžadujú: {1}"
                            ).format(pkg, ", ".join(deps))
                            log_widget.append(msg)
                            worker.success = False
                            if hasattr(worker, 'signals'):
                                worker.signals.finished.emit()
                            return

                is_upgrade = "install" in cmd_lower and ("--upgrade" in worker.cmd or "-U" in worker.cmd)
                is_req_install = "install" in cmd_lower and "-r" in cmd_lower
                
                uninstalled_pkgs = AptListener._extract_packages_from_uninstall_cmd(worker.cmd) if is_uninstall else []
                installed_pkgs = AptListener._extract_packages_from_install_cmd(worker.cmd) if "install" in cmd_lower else []
            else:
                is_uninstall = False
                is_upgrade = True
                is_req_install = False
                uninstalled_pkgs = []
                installed_pkgs = []

            should_autoremove = is_uninstall or is_upgrade
            released_reqs = []
            for pkg in uninstalled_pkgs:
                released_reqs.extend(AptListener._get_requires_for_package(worker.venv_path, pkg, core.package_manager))

            def apt_callback():
                success = getattr(worker, 'success', True)
                if not success:
                    log_widget.append("⚠️ [APT] Operácia zlyhala — APT stav ostáva nezmenený.")
                else:
                    for pkg in uninstalled_pkgs:
                        AptLogic.unmark_explicit(worker.venv_path, pkg)
                    for pkg in installed_pkgs:
                        AptLogic.mark_as_explicit(worker.venv_path, pkg)
                    if is_req_install:
                        AptLogic.install_sync(core, worker.venv_path, log_widget.append)
                    if should_autoremove:
                        AptLogic.autoremove(core, worker.venv_path, log_widget.append, released_packages=released_reqs)

            worker.signals.finished.connect(apt_callback)
            orig_run_pip_task(worker, log_widget)

        PipManager._run_pip_task = patched_run_pip_task

    @staticmethod
    def _patch_pip_package_widget(core):
        from windows.pip_package_widget import PipPackageWidget
        orig_run_pip_command = PipPackageWidget.run_pip_command

        def patched_run_pip_command(self, full_command, start_message):
            cmd_lower = [x.lower() for x in full_command]
            is_uninstall = "uninstall" in cmd_lower

            if is_uninstall:
                pkgs_to_uninstall = AptListener._extract_packages_from_uninstall_cmd(full_command)
                for pkg in pkgs_to_uninstall:
                    deps = AptListener._is_package_required_by_others(self.venv_path, core, pkg)
                    if deps:
                        msg = LanguageManager.get(
                            "apt_err_cannot_uninstall",
                            "❌ Nemožno odinštalovať '{0}', pretože ho vyžadujú: {1}"
                        ).format(pkg, ", ".join(deps))
                        self.log(msg)
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "Chyba", msg)
                        return

            is_upgrade = "install" in cmd_lower and ("--upgrade" in full_command or "-U" in full_command)
            should_autoremove = is_uninstall or is_upgrade

            uninstalled_pkgs = AptListener._extract_packages_from_uninstall_cmd(full_command) if is_uninstall else []
            installed_pkgs = AptListener._extract_packages_from_install_cmd(full_command) if "install" in full_command else []

            released_reqs = []
            for pkg in uninstalled_pkgs:
                released_reqs.extend(AptListener._get_requires_for_package(self.venv_path, pkg, core.package_manager))

            orig_run_pip_command(self, full_command, start_message)

            def on_finished(exit_code):
                if exit_code != 0:
                    self.log(f"⚠️ [APT] Pip operácia zlyhala (kód={exit_code}) — APT stav ostáva nezmenený.")
                    return
                for pkg in uninstalled_pkgs:
                    AptLogic.unmark_explicit(self.venv_path, pkg)
                for pkg in installed_pkgs:
                    AptLogic.mark_as_explicit(self.venv_path, pkg)
                if should_autoremove:
                    AptLogic.autoremove(core, self.venv_path, self.log, released_packages=released_reqs)

            if hasattr(self, 'worker') and self.worker:
                self.worker.finished.connect(on_finished)

        PipPackageWidget.run_pip_command = patched_run_pip_command

    @staticmethod
    def _patch_pipe_install(core):
        from core.logic.pip_e import PipEInstallWorker
        orig_init = PipEInstallWorker.__init__

        def patched_init(self, venv_path, target_path):
            orig_init(self, venv_path, target_path)

            def on_finished_install(success):
                if success:
                    AptLogic.install_sync(core, self.venv_path, self.log_msg.emit)

            self.finished.connect(on_finished_install)

        PipEInstallWorker.__init__ = patched_init

    @staticmethod
    def _patch_pipe_uninstall(core):
        from core.logic.pip_e import PipEUninstallWorker
        orig_init = PipEUninstallWorker.__init__
        orig_run = PipEUninstallWorker.run

        def patched_init(self, venv_path, package_name):
            orig_init(self, venv_path, package_name)

            released_reqs = AptListener._get_requires_for_package(self.venv_path, self.package_name, core.package_manager)

            def on_finished_uninstall(success):
                if success:
                    AptLogic.unmark_explicit(self.venv_path, self.package_name)
                    AptLogic.autoremove(core, self.venv_path, self.log_msg.emit, released_packages=released_reqs)

            self.finished.connect(on_finished_uninstall)

        def patched_run(self):
            deps = AptListener._is_package_required_by_others(self.venv_path, core, self.package_name)
            if deps:
                msg = LanguageManager.get(
                    "apt_err_cannot_uninstall",
                    "❌ Nemožno odinštalovať '{0}', pretože ho vyžadujú: {1}"
                ).format(self.package_name, ", ".join(deps))
                self.log_msg.emit(msg)
                self.finished.emit(False)
                return

            orig_run(self)

        PipEUninstallWorker.__init__ = patched_init
        PipEUninstallWorker.run = patched_run

    @staticmethod
    def _patch_local_linker(core):
        from core.logic.button.manager.local_packages_linker import LocalPackagesLinker
        orig_apply_changes = LocalPackagesLinker.apply_changes

        def patched_apply_changes(self, selected_items_data):
            effective_core = getattr(self, "core", core)
            old_linked = self.parent._get_linked_packages()
            new_linked = set(item['name'] for item in selected_items_data)
            
            released_reqs = []
            for old_pkg in old_linked:
                if old_pkg not in new_linked:
                    pkg_path = os.path.join(effective_core.local_packages_root, old_pkg)
                    meta_path = os.path.join(pkg_path, "local_meta.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                released_reqs.extend(meta.get("requires_pip", []))
                        except Exception: pass

            result = orig_apply_changes(self, selected_items_data)
            
            if result and released_reqs:
                AptLogic.autoremove(effective_core, self.venv_path, self.log_callback, released_packages=released_reqs)
                
            return result

        LocalPackagesLinker.apply_changes = patched_apply_changes