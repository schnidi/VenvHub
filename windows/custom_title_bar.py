"""
Súbor: windows/custom_title_bar.py
Univerzálna titulková lišta, ktorú používajú okná v aplikácii.
"""

import os
from PyQt6.QtWidgets import QWidget
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from core._path import Paths
from core.logic.sluzby.about_logic import AboutLogic


class CustomTitleBar(QWidget):
    """Univerzálna titulková lišta, ktorú používajú okná v aplikácii."""

    def __init__(self, parent):
        """
        Inicializácia titulkovej lišty, načítanie UI šablóny a nastavenie ikon.
        """
        super().__init__(parent)
        self.parent_window = parent
        
        """Načítanie grafického rozhrania titulkovej lišty."""
        uic.loadUi(Paths.get_ui_file_path("custom_title_bar.ui"), self)

        """Zakázanie automatického škálovania QLabelu ikony."""
        self.lbl_icon.setScaledContents(False)

        self.old_pos = None

        """Prepojenie signálov a nastavenie titulku a ikon."""
        self.connect_signals()
        self.setup_from_parent()

    def connect_signals(self):
        """Prepojenie tlačidiel lišty s funkciami rodičovského okna."""
        self.btn_minimize.clicked.connect(self.parent_window.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize_restore)
        self.btn_close.clicked.connect(self.parent_window.close)
        
        """Prepojenie tlačidla 'O programe' (About)."""
        self.btn_about.clicked.connect(self.show_about_dialog)

    def setup_from_parent(self):
        """Prevezme titulok a ikony pre panel z rodičovského okna."""
        self.lbl_title.setText(self.parent_window.windowTitle())
        
        """Nastavenie hlavnej ikony okna z app.ico."""
        icon_path = Paths.get_icon_path("app.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            size = 30
            self.lbl_icon.setFixedSize(size, size)
            smooth_pixmap = icon.pixmap(size, size)
            self.lbl_icon.setPixmap(smooth_pixmap)
        else:
            self.lbl_icon.hide()
            
        """Nastavenie ikony pre tlačidlo 'About' (O programe)."""
        about_icon_path = Paths.get_icon_path("about.svg")
        if os.path.exists(about_icon_path):
            self.btn_about.setIcon(QIcon(about_icon_path))
            self.btn_about.setIconSize(QSize(18, 18))

    def show_about_dialog(self):
        """Zobrazí okno 'O programe' pomocou centrálnej služby AboutLogic."""
        AboutLogic.show_about_dialog(self.parent_window)

    def toggle_maximize_restore(self):
        """Pre maximalizáciu a obnovu okna."""
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_maximize.setText("🗖")
        else:
            self.parent_window.showMaximized()
            self.btn_maximize.setText("🗗")

    def mousePressEvent(self, event):
        """Zachytí stlačenie ľavého tlačidla myši pre začiatok presúvania okna."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Sleduje pohyb myši a posúva rodičovské okno po obrazovke."""
        if self.old_pos and not self.parent_window.isMaximized():
            delta = event.globalPosition().toPoint() - self.old_pos
            self.parent_window.move(
                self.parent_window.x() + delta.x(), 
                self.parent_window.y() + delta.y()
            )
            self.old_pos = event.globalPosition().toPoint()
            
    def mouseReleaseEvent(self, event):
        """Uvoľní pozíciu po pustení tlačidla myši."""
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        """Dvojklik na lištu prepína medzi maximalizovaným a normálnym stavom okna."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize_restore()