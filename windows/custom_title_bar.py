#----------------------------------------
# Súbor: windows/custom_title_bar.py
#----------------------------------------

import os
import json
from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from core._path import Paths
from core.logic.language_manager import LanguageManager


class CustomTitleBar(QWidget):
    """Univerzálna titulková lišta, ktorú teraz používajú všetky okná."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        
        # 1. Načítame UI
        uic.loadUi(Paths.get_ui_file_path("custom_title_bar.ui"), self)

        # 2. Zakážeme akékoľvek automatické škálovanie QLabelu
        self.lbl_icon.setScaledContents(False)

        self.old_pos = None

        # 3. Prepojíme tlačidlá
        self.connect_signals()
        
        # 4. Nastavíme titulok a ikony
        self.setup_from_parent()

    def connect_signals(self):
        """Prepojenie tlačidiel lišty s funkciami rodičovského okna."""
        self.btn_minimize.clicked.connect(self.parent_window.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize_restore)
        self.btn_close.clicked.connect(self.parent_window.close)
        
        # Prepojenie About tlačidla (ak je to hlavné okno)
        self.btn_about.clicked.connect(self.show_about_dialog)

    def setup_from_parent(self):
        """Prevezme titulok a ikony pre panel."""
        self.lbl_title.setText(self.parent_window.windowTitle())
        
        # === Nastavenie hlavnej ikony okna ===
        icon_path = Paths.get_icon_path("app.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            size = 30
            self.lbl_icon.setFixedSize(size, size)
            smooth_pixmap = icon.pixmap(size, size)
            self.lbl_icon.setPixmap(smooth_pixmap)
        else:
            self.lbl_icon.hide()
            
        # === Nastavenie ikony pre tlačidlo "About" ===
        about_icon_path = Paths.get_icon_path("about.svg")
        if os.path.exists(about_icon_path):
            self.btn_about.setIcon(QIcon(about_icon_path))
            self.btn_about.setIconSize(QSize(18, 18))

    def show_about_dialog(self):
        """Načíta JSON a zobrazí HTML v informačnom okne spolu s certifikátom."""
        json_path = os.path.join(Paths.get_base_path(), Paths.ASSETS_DIR_NAME, "about.json")
        
        html_content = LanguageManager.get("about_fallback_html", "<p>O programe</p>")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 1. Zistíme aktuálny kód jazyka (napr. 'fr_FR')
                    current_lang = LanguageManager._current_lang_code
                    lang_key = f"about_html_{current_lang}"
                    
                    # 2. KASKÁDOVÝ FALLBACK (Ochrana proti chýbajúcemu prekladu)
                    if lang_key in data:
                        # Ak preklad existuje (napr. fr_FR), daj ho
                        html_content = data[lang_key]
                    elif "about_html_en_US" in data:
                        # Ak neexistuje, daj ako HLAVNÚ ZÁCHRANU Angličtinu
                        html_content = data["about_html_en_US"]
                    elif "about_html_sk_SK" in data:
                        # Ak nie je ani EN (čo by sa nemalo stať), daj aspoň SK
                        html_content = data["about_html_sk_SK"]
                    elif "about_html" in data:
                        # Spätná kompatibilita pre staré súbory
                        html_content = data["about_html"]

            except Exception as e:
                html_content = LanguageManager.get("about_err_load", "<p>Chyba pri načítaní info: {0}</p>").format(e)
                
        # Lokálny import zamedzuje cyklickému importovaniu počas načítania modulov
        from windows.about_dialog import AboutDialog
        dialog = AboutDialog(self.parent_window, html_content)
        dialog.exec()

    def toggle_maximize_restore(self):
        """Pre maximalizáciu a obnovu okna."""
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_maximize.setText("🗖")
        else:
            self.parent_window.showMaximized()
            self.btn_maximize.setText("🗗")

    # === LOGIKA PRE PRESÚVANIE OKNA MYŠOU ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos and not self.parent_window.isMaximized():
            delta = event.globalPosition().toPoint() - self.old_pos
            self.parent_window.move(
                self.parent_window.x() + delta.x(), 
                self.parent_window.y() + delta.y()
            )
            self.old_pos = event.globalPosition().toPoint()
            
    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize_restore()