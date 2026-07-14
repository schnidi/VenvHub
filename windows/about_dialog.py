#----------------------------------------
# Súbor: windows/about_dialog.py
#----------------------------------------

import os
import json
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QFrame, QWidget
from PyQt6.QtCore import Qt
from core._path import Paths
from core.logic.language_manager import LanguageManager


class AboutDialog(QDialog):
    """Vlastné okno 'O programe' s našou custom lištou a podporou rodného listu."""
    def __init__(self, parent, html_content):
        super().__init__(parent)
        self.setWindowTitle(LanguageManager.get("title_about", "O programe"))
        self.setMinimumWidth(450)
        
        # 1. Zrušíme štandardný Windows rám
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("AboutDialog") # Umožní napojenie na CSS pre okraje

        # 2. Hlavný layout BEZ OKRAJOV, aby naša lišta sadla na milimeter
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1) # 1px okraj kvôli dizajnu
        self.main_layout.setSpacing(0)
        # Ochrana pred Windows DWM bugom: Okno sa bude automaticky a dokonale scvrkávať/rozťahovať samo
        self.main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        # 3. Vložíme našu Custom Title Bar a skryjeme zbytočné tlačidlá
        # Lokálny import zamedzuje cyklickému importovaniu medzi panelom a dialógom
        from windows.custom_title_bar import CustomTitleBar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.btn_minimize.hide()
        self.title_bar.btn_maximize.hide()
        self.title_bar.btn_about.hide() # V "O programe" nepotrebujeme tlačidlo "O programe"
        self.main_layout.addWidget(self.title_bar)

        # 4. Vnútorný kontajner (s okrajmi pre texty)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # -- HTML Obsah (Hlavička, Info) --
        self.lbl_info = QLabel(html_content)
        self.lbl_info.setOpenExternalLinks(True)
        self.lbl_info.setWordWrap(True)
        content_layout.addWidget(self.lbl_info)

        # -- Vodorovná oddeľovacia čiara --
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(line)

        # -- Tlačidlo na zobrazenie rodného listu --
        btn_show_text = LanguageManager.get("btn_show_cert", "▶ Zobraziť technické detaily (Rodný list)")
        self.btn_toggle_cert = QPushButton(btn_show_text)
        self.btn_toggle_cert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_cert.setCheckable(True)
        self.btn_toggle_cert.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #007acc;
                border: none;
                text-align: left;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.btn_toggle_cert.clicked.connect(self.toggle_certificate)
        content_layout.addWidget(self.btn_toggle_cert)

        # -- Textové pole pre výpis certifikátu (predvolene skryté) --
        self.txt_cert = QTextEdit()
        self.txt_cert.setReadOnly(True)
        self.txt_cert.setMinimumHeight(200)
        self.txt_cert.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas; font-size: 12px; padding: 5px;")
        self.txt_cert.hide()
        content_layout.addWidget(self.txt_cert)

        # -- Spodné tlačidlo OK --
        btn_close_text = LanguageManager.get("btn_close_dialog", "Zavrieť")
        self.btn_ok = QPushButton(btn_close_text)
        self.btn_ok.setFixedWidth(100)
        self.btn_ok.clicked.connect(self.accept)
        
        # Vycentrovanie tlačidla OK
        bottom_layout = QVBoxLayout()
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.btn_ok, alignment=Qt.AlignmentFlag.AlignCenter)
        content_layout.addLayout(bottom_layout)

        # Vloženie celého kontentu do hlavného layoutu
        self.main_layout.addWidget(self.content_widget)

        # Načítanie najnovšieho rodného listu priamo do pamäte
        self.load_latest_certificate()

    def load_latest_certificate(self):
        """Vyhľadávanie a parsovanie najnovšieho rodného listu."""
        search_dirs = [
            Paths.get_app_root_path(),  
            Paths.get_base_path(),      
            os.path.join(Paths.get_app_root_path(), Paths.ASSETS_DIR_NAME),
            os.path.join(Paths.get_base_path(), Paths.ASSETS_DIR_NAME)
        ]

        cert_files = []
        for d in set(search_dirs):
            if os.path.exists(d):
                try:
                    for f in os.listdir(d):
                        if f.endswith("birth_certificate.json"):
                            cert_files.append(os.path.join(d, f))
                except Exception:
                    pass

        latest_cert = None
        latest_sort_key = ""

        for file_path in cert_files:
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    
                    date_str = str(data.get("build_date") or data.get("last_updated") or data.get("created_at") or "")
                    if not date_str:
                        mtime = os.path.getmtime(file_path)
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

                    if date_str > latest_sort_key:
                        latest_sort_key = date_str
                        latest_cert = data
                        latest_cert['_actual_date_str'] = date_str 
                        latest_cert['_filepath'] = file_path       
            except Exception as e:
                print(f"[AboutDialog] Ignorujem neplatný certifikát: {file_path} - Chyba: {e}")
                continue

        if latest_cert:
            filename = os.path.basename(latest_cert.get('_filepath', ''))
            
            txt_header = LanguageManager.get("cert_header", "--- NAJNOVŠÍ RODNÝ LIST ({0}) ---").format(filename)
            txt_type = LanguageManager.get("cert_type", "Typ dokumentu: {0}")
            txt_date = LanguageManager.get("cert_date", "Dátum buildu: {0}")
            txt_python = LanguageManager.get("cert_python", "Python: {0}")
            txt_deps = LanguageManager.get("cert_deps", "Závislosti a balíčky ({0}):")
            
            info = f"{txt_header}\n"
            
            doc_type = latest_cert.get('document_type', LanguageManager.get("cert_unknown", "Neznámy"))
            info += f"{txt_type.format(doc_type)}\n"
            info += f"{txt_date.format(latest_cert.get('_actual_date_str'))}\n"
            
            env = latest_cert.get('python_environment', {})
            python_ver = env.get('python_version') or latest_cert.get('python_version', LanguageManager.get("cert_unknown", "Neznámy"))
            info += f"{txt_python.format(python_ver)}\n\n"
            
            packages = env.get('installed_packages') or latest_cert.get('packages', [])
            info += f"{txt_deps.format(len(packages))}\n"
            
            for pkg in sorted(packages, key=lambda x: x.get('name', '').lower()):
                info += f" - {pkg.get('name')} (v{pkg.get('version')})\n"
                
            self.txt_cert.setPlainText(info)
        else:
            fallback_msg = LanguageManager.get(
                "cert_not_found", 
                "Rodný list nebol nájdený.\n\nAplikácia hľadala súbory končiace na '_birth_certificate.json'\nv priečinku: {0}"
            ).format(Paths.get_app_root_path())
            self.txt_cert.setPlainText(fallback_msg)

    def toggle_certificate(self, checked):
        """Zobrazí alebo skryje pole s technickými detailmi."""
        if checked:
            self.txt_cert.show()
            self.btn_toggle_cert.setText(LanguageManager.get("btn_hide_cert", "▼ Skryť technické detaily"))
        else:
            self.txt_cert.hide()
            self.btn_toggle_cert.setText(LanguageManager.get("btn_show_cert", "▶ Zobraziť technické detaily (Rodný list)"))
            
            # --- OPRAVA SKÁKANIA BEZRÁMOVÉHO OKNA ---
            # Vynútime zneplatnenie cache rozloženia a jeho okamžitý prepočet
            self.layout().invalidate()
            self.layout().activate()
            # Explicitne zmenšíme fyzické okno na výšku jeho minimálnych potrieb
            self.resize(self.width(), self.minimumSizeHint().height())