#----------------------------------------
# Súbor: core/logic/sluzby/windows_location.py
#----------------------------------------

import os
import json
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QGuiApplication
from core._path import Paths

class WindowLocation:
    """
    Univerzálna služba na ukladanie a načítavanie pozícií (súradníc) okien.
    Dáta ukladá do samostatného súboru window_positions.json.
    """
    
    @staticmethod
    def _get_file_path():
        # Uložíme to do rovnakého priečinka ako hlavný config, ale oddelene
        base_dir = os.path.dirname(Paths.get_config_file_path())
        return os.path.join(base_dir, "window_positions.json")

    @staticmethod
    def _load_all() -> dict:
        path = WindowLocation._get_file_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def _save_all(data: dict):
        path = WindowLocation._get_file_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    @staticmethod
    def save_position(widget: QWidget, window_name: str):
        """
        Prečíta aktuálnu X, Y pozíciu okna a uloží ju pod zadaným menom.
        Zavolaj túto metódu pri zatváraní okna (napr. v closeEvent).
        """
        data = WindowLocation._load_all()
        data[window_name] = {"x": widget.x(), "y": widget.y()}
        WindowLocation._save_all(data)

    @staticmethod
    def restore_position(widget: QWidget, window_name: str):
        """
        Načíta X, Y pozíciu pre dané meno a presunie okno.
        Obsahuje ochranu: ak bol odpojený monitor a pozícia je mimo obrazovky, ignoruje ju.
        Zavolaj túto metódu na konci funkcie __init__ v okne.
        """
        data = WindowLocation._load_all()
        if window_name in data:
            pos = data[window_name]
            x, y = pos.get("x"), pos.get("y")
            
            if x is not None and y is not None:
                # Ochrana: Existuje táto súradnica na nejakom aktuálne pripojenom monitore?
                is_valid = False
                for screen in QGuiApplication.screens():
                    if screen.geometry().contains(x, y):
                        is_valid = True
                        break
                        
                if is_valid:
                    widget.move(x, y)