#----------------------------------------
# Súbor: core/logic/vscode_user/system_sync.py
#----------------------------------------

import os
import shutil
from PyQt6.QtCore import QObject, pyqtSignal, QCoreApplication
from core.logic.sluzby.copy_del import CopyDelService
from core.logic.language_manager import LanguageManager

class SystemSyncWorker(QObject):
    log_msg = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, profile_dir: str, is_new_profile: bool = False):
        super().__init__()
        self.profile_dir = profile_dir
        self.is_new_profile = is_new_profile
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        target_user_data = os.path.join(self.profile_dir, "data", "User")
        target_extensions = os.path.join(self.profile_dir, "data", "extensions")

        appdata = os.environ.get('APPDATA')
        userprofile = os.environ.get('USERPROFILE')

        if not appdata or not userprofile:
            self.log_msg.emit(LanguageManager.get("err_system_vars", "❌ CHYBA: Nepodarilo sa získať systémové premenné."))
            self.finished.emit(False, "ERROR")
            return

        sys_user_data = os.path.join(appdata, "Code", "User")
        sys_extensions = os.path.join(userprofile, ".vscode", "extensions")

        # 1. User Data
        self.log_msg.emit(LanguageManager.get("msg_processing_user_data", "\n⏳ Spracovávam nastavenia (User data)..."))
        def check_cancelled_user():
            QCoreApplication.processEvents()
            return self._is_cancelled

        res_user = CopyDelService.safe_copy_with_rollback(
            src_path=sys_user_data,
            dst_path=target_user_data,
            is_cancelled_func=check_cancelled_user,
            log_func=self.log_msg.emit,
            progress_func=self.progress_percent.emit,
            delete_full_dst_on_rollback=True # Ak zrušíme, zmažeme celú cieľovú User zložku
        )

        if not res_user["success"]:
            self._handle_failure(res_user)
            return

        # 2. Extensions
        self.log_msg.emit(LanguageManager.get("msg_processing_extensions", "\n⏳ Spracovávam rozšírenia (Extensions)..."))
        def check_cancelled_ext():
            QCoreApplication.processEvents()
            return self._is_cancelled

        res_ext = CopyDelService.safe_copy_with_rollback(
            src_path=sys_extensions,
            dst_path=target_extensions,
            is_cancelled_func=check_cancelled_ext,
            log_func=self.log_msg.emit,
            progress_func=self.progress_percent.emit,
            delete_full_dst_on_rollback=True
        )

        if not res_ext["success"]:
            self._handle_failure(res_ext)
            return

        self.log_msg.emit(LanguageManager.get("msg_import_success", "🎉 Import zo systému úspešne dokončený!"))
        self.finished.emit(True, "OK")

    def _handle_failure(self, result):
        if result["reason"] == "CANCELLED":
            if self.is_new_profile:
                self.log_msg.emit(LanguageManager.get("msg_removing_incomplete_profile", "🧹 Odstraňujem neúplný profil..."))
                
                # --- OPRAVA: Extrémne silné mazanie namiesto obyčajného shutil.rmtree ---
                CopyDelService.safe_delete_with_progress(self.profile_dir)
                
            self.finished.emit(False, "CANCELLED")
        else:
            self.finished.emit(False, result["reason"])
