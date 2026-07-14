#----------------------------------------
# Súbor: windows/build_log_dialog.py
#----------------------------------------

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QWidget
from PyQt6.QtCore import Qt
from core.logic.py_installer.worker import PyInstallerWorker
from core.logic.language_manager import LanguageManager

# Import našej titulkovej lišty
from windows.custom_title_bar import CustomTitleBar


class BuildLogDialog(QDialog):
    def __init__(self, parent, command_list, project_path):
        super().__init__(parent)
        self.command_list = command_list
        self.project_path = project_path  # Uloženie cesty k projektu
        
        self.setWindowTitle(LanguageManager.get("title_build_log", "PyInstaller Build Log"))
        self.resize(700, 500)
        self.setObjectName("BuildLogDialog")
        
        # 1. Zrušíme štandardný Windows rám
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # 2. Hlavný layout okna bez okrajov pre titulkovú lištu
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1) # 1px okraj kvôli viditeľnosti rámčeka
        self.main_layout.setSpacing(0)
        
        # 3. Vložíme našu Custom Title Bar a skryjeme nepotrebné tlačidlá
        self.title_bar = CustomTitleBar(self)
        self.title_bar.btn_minimize.hide()
        self.title_bar.btn_maximize.hide()
        self.title_bar.btn_about.hide()
        self.main_layout.addWidget(self.title_bar)
        
        # 4. Vnútorný kontajner s okrajmi pre samotný obsah logu
        self.content_widget = QWidget()
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Info Label
        self.lbl_status = QLabel(LanguageManager.get("lbl_build_running", "Prebieha Build..."), self)
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #007acc;")
        layout.addWidget(self.lbl_status)

        # Log Console
        self.text_log = QTextEdit(self)
        self.text_log.setReadOnly(True)
        self.text_log.setStyleSheet("background-color: #000; color: #ccc; font-family: Consolas;")
        layout.addWidget(self.text_log)

        # Close/Cancel Button
        self.btn_close = QPushButton(LanguageManager.get("btn_cancel_or_close", "Zrušiť / Zavrieť"), self)
        self.btn_close.clicked.connect(self.on_close_click)
        layout.addWidget(self.btn_close)
        
        # Pridáme vnútorný kontajner do hlavného layoutu pod lištu
        self.main_layout.addWidget(self.content_widget)

        # Worker
        self.worker = PyInstallerWorker(self.command_list, self.project_path)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_finished)
        
        # Štart
        self.worker.start()

    def append_log(self, text):
        self.text_log.append(text)
        # Autoscroll
        sb = self.text_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_finished(self, success):
        if success:
            self.lbl_status.setText(LanguageManager.get("lbl_build_done", "✅ HOTOVO - ÚSPEŠNÉ"))
            self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #2ecc71;")
        else:
            self.lbl_status.setText(LanguageManager.get("lbl_build_failed", "❌ CHYBA - NEÚSPEŠNÉ"))
            self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #e74c3c;")
        
        self.btn_close.setText(LanguageManager.get("btn_close_dialog", "Zavrieť"))

    def on_close_click(self):
        if self.worker.isRunning():
            self.worker.kill()
            self.text_log.append("\n" + LanguageManager.get("msg_build_interrupted", "--- PROCES BOL PRERUŠENÝ POUŽÍVATEĽOM ---"))
        self.accept()