#----------------------------------------
# Súbor: core/logic/sluzby/win_admin.py
#----------------------------------------

import ctypes
from ctypes import wintypes
import os
import time

# Konštanty pre Windows API
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_HIDE = 0
WAIT_TIMEOUT = 0x00000102

class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class WinAdmin:
    """Služba pre prácu s administrátorskými právami vo Windowse."""

    @staticmethod
    def is_admin() -> bool:
        """Zistí, či je samotná aplikácia momentálne plne spustená ako administrátor."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def needs_admin_for_path(target_path: str) -> bool:
        """Zistí, či inštalácia na zadanú cestu vyžaduje administrátora (napr. Program Files)."""
        if WinAdmin.is_admin():
            return False
            
        program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
        
        target_lower = target_path.lower()
        pf_lower = program_files.lower()
        pfx86_lower = program_files_x86.lower()
        
        if target_lower.startswith(pf_lower) or target_lower.startswith(pfx86_lower):
            return True
            
        return False

    @staticmethod
    def _run_uac_process(bat_path: str, marker_path: str, state_callback=None) -> bool:
        """Interná služba, ktorá bezpečne spúšťa UAC proces a prečíta jeho stavy z markeru."""
        
        # Pripravíme začiatočný stav
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write("[STATUS] UAC_APPROVED")

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.lpVerb = "runas"
        sei.lpFile = bat_path
        sei.nShow = SW_HIDE  # Okno bude absolútne skryté

        # Otvoríme proces cez UAC
        if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
            return False # Používateľ stlačil "Nie" v UAC okne, alebo proces zlyhal pri štarte

        hProcess = sei.hProcess
        if not hProcess:
            return False

        last_state = ""
        success = False

        # --- NATÍVNA WINDOWS SLUČKA (Cez Handle) ---
        while True:
            # 1. Čítanie stavov z markeru
            if os.path.exists(marker_path):
                try:
                    with open(marker_path, 'r', encoding='utf-8') as f:
                        current_state = f.read().strip()
                        
                    # Ak nastala zmena, ohlásime to pomocou Callbacku
                    if current_state and current_state != last_state:
                        last_state = current_state
                        if state_callback:
                            state_callback(current_state)
                            
                        # Ak je koniec, môžeme cyklus opustiť skoršie
                        if current_state == "[STATUS] DONE":
                            success = True
                            break 
                except Exception:
                    # Súbor môže byť práve v stave zápisu (Lock), preskočíme tento cyklus
                    pass
                    
            # 2. Skontrolujeme, či proces ešte žije (timeout 100ms namiesto time.sleep)
            wait_result = ctypes.windll.kernel32.WaitForSingleObject(hProcess, 100)
            if wait_result != WAIT_TIMEOUT:
                # WAIT_TIMEOUT znamená, že proces ešte beží. 
                # Ak vráti niečo iné (napr. 0), znamená to, že proces umrel/skončil.
                break

        # Pre istotu, ak proces umrel extrémne rýchlo, skontrolujeme posledný stav
        if not success and os.path.exists(marker_path):
             try:
                with open(marker_path, 'r', encoding='utf-8') as f:
                    if f.read().strip() == "[STATUS] DONE":
                        success = True
             except Exception:
                pass

        # Zatvoríme Handle, čím proces bezpečne odomkneme pre systémový zber odpadu
        ctypes.windll.kernel32.CloseHandle(hProcess)
        return success


    @staticmethod
    def move_directory_with_uac(src: str, dst: str, state_callback=None) -> bool:
        """
        Kopíruje a presúva adresáre cez UAC, komunikuje reálny stav.
        """
        parent_dst = os.path.dirname(dst)
        src = src.rstrip("\\/")
        dst = dst.rstrip("\\/")
        parent_dst = parent_dst.rstrip("\\/")
        
        temp_dir = os.environ.get('TEMP', 'C:\\Temp')
        marker_path = os.path.join(temp_dir, f"uac_move_{int(time.time()*1000)}.marker")
        bat_path = os.path.join(temp_dir, f"uac_move_{int(time.time()*1000)}.bat")
        
        bat_content = f"""@echo off
chcp 65001 > nul
echo [STATUS] PREPARING > "{marker_path}"
if not exist "{parent_dst}" mkdir "{parent_dst}"
echo [STATUS] COPYING > "{marker_path}"
xcopy "{src}" "{dst}" /E /I /H /Y /Q
if %errorlevel% neq 0 (
    echo [STATUS] ERROR_COPY > "{marker_path}"
    exit /b %errorlevel%
)
if exist "{dst}\\install.ini" (
    echo [STATUS] CLEANING > "{marker_path}"
    rmdir /S /Q "{src}"
)
echo [STATUS] DONE > "{marker_path}"
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
        except Exception:
            return False
            
        # Zavoláme nový procesný exekútor
        success = WinAdmin._run_uac_process(bat_path, marker_path, state_callback)
        
        # Upratovanie po sebe
        time.sleep(0.5)
        try: os.remove(bat_path)
        except: pass
        try: os.remove(marker_path)
        except: pass
            
        if not success:
            return False
            
        return os.path.exists(dst) and os.path.exists(os.path.join(dst, "install.ini"))


    @staticmethod
    def run_cmd_with_uac_and_wait(cmd_string: str, marker_path: str, state_callback=None) -> bool:
        """
        Vykonáva sériu príkazov cez UAC, komunikuje reálny stav.
        """
        temp_dir = os.environ.get('TEMP', 'C:\\Temp')
        bat_path = os.path.join(temp_dir, f"uac_cmd_{int(time.time()*1000)}.bat")

        bat_content = f"""@echo off
chcp 65001 > nul
{cmd_string}
if %errorlevel% neq 0 (
    echo [STATUS] ERROR > "{marker_path}"
    exit /b %errorlevel%
)
echo [STATUS] DONE > "{marker_path}"
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
        except Exception:
            return False
            
        # Zavoláme nový procesný exekútor
        success = WinAdmin._run_uac_process(bat_path, marker_path, state_callback)
        
        # Upratovanie po sebe
        time.sleep(0.5)
        try: os.remove(bat_path)
        except: pass
        try: os.remove(marker_path)
        except: pass
            
        return success