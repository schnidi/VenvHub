#----------------------------------------
# Súbor: windows/progress_dialog.py
#----------------------------------------

from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QTextEdit, QPushButton, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from core.logic.language_manager import LanguageManager

# --- PRIDANÝ IMPORT PRE NAŠU VLASTNÚ LIŠTU ---
from windows.custom_title_bar import CustomTitleBar

class ProgressDialog(QDialog):
    # Signál pre zrušenie operácie
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProgressDialog")
        
        # Zrušíme štandardný Windows rámček
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setMinimumWidth(450)

        # Hlavný layout okna bez okrajov (aby lišta pekne sadla)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(0)

        # --- VLOŽENIE NAŠEJ VLASTNEJ LIŠTY ---
        self.title_bar = CustomTitleBar(self)
        # Schováme zbytočné tlačidlá, necháme len krížik "X"
        self.title_bar.btn_minimize.hide()
        self.title_bar.btn_maximize.hide()
        self.title_bar.btn_about.hide()
        self.main_layout.addWidget(self.title_bar)

        # Vnútorný kontajner (s okrajmi pre obsah)
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        self.message_label = QLabel(LanguageManager.get("msg_please_wait", "Prosím, čakajte..."))
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        # Tmavý štýl konzoly
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 12px; padding: 5px;")
        self.layout.addWidget(self.log_output)

        self.btn_cancel = QPushButton(LanguageManager.get("btn_cancel", "Zrušiť operáciu"))
        self.btn_cancel.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 5px;")
        self.btn_cancel.hide() 
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        self.layout.addWidget(self.btn_cancel)

        self.main_layout.addWidget(self.content_widget)

    def setWindowTitle(self, title):
        """Prepíšeme, aby sa text posunul do našej vlastnej lišty."""
        super().setWindowTitle(title)
        if hasattr(self, 'title_bar'):
            self.title_bar.lbl_title.setText(title)

    def closeEvent(self, event):
        """Inteligentné správanie pri kliknutí na 'X'."""
        # Ak je zobrazené červené tlačidlo Zrušiť, dovolíme to zrušiť aj krížikom
        if self.btn_cancel.isVisible() and self.btn_cancel.isEnabled():
            self._on_cancel_clicked()
            event.ignore() # Nezatvoríme ihneď, počkáme kým sa operácia reálne ukončí
        else:
            # Ak beží kritická operácia (napr. mazanie Venvu), zakážeme zatvorenie okna natvrdo!
            event.ignore()

    def set_message(self, text):
        self.message_label.setText(text)

    def add_log_message(self, message):
        """Pridá text do okna a posunie rolovaciu lištu nadol."""
        self.log_output.append(message)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def enable_cancel_button(self):
        """Zobrazí tlačidlo Zrušiť pre operácie, ktoré to podporujú (napr. kopírovanie)."""
        self.btn_cancel.show()

    def _on_cancel_clicked(self):
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setText(LanguageManager.get("msg_cancelling", "Ruším operáciu, prosím čakajte..."))
        self.cancelled.emit()

    def set_progress_mode(self, indeterminate=True):
        """Prepína medzi behačkou (0,0) a reálnymi percentami (0,100)."""
        if indeterminate:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setTextVisible(False)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setValue(0)

    def set_progress_value(self, value):
        """Nastaví konkrétnu hodnotu na Progress Bare."""
        self.progress_bar.setValue(value)