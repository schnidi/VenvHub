import os
import ctypes
from ctypes import wintypes

class DiskUUIDHelper:
    @staticmethod
    def get_drive_uuid(path: str) -> str:
        """
        Vráti Volume Serial Number (UUID) disku pre danú cestu.
        Používa GetVolumeInformationW – rýchle, bez admin práv, nezávislé od lokalizácie.
        """
        if not path:
            return ""
        # Získa koreň disku (napr. "C:\\")
        drive = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
        
        volume_serial = wintypes.DWORD()
        success = ctypes.windll.kernel32.GetVolumeInformationW(
            drive,           # lpRootPathName
            None,            # lpVolumeNameBuffer (nechceme)
            0,               # nVolumeNameSize
            ctypes.byref(volume_serial),  # lpVolumeSerialNumber
            None,            # lpMaximumComponentLength
            None,            # lpFileSystemFlags
            None,            # lpFileSystemNameBuffer
            0                # nFileSystemNameSize
        )
        if success:
            # Formát rovnako ako "vol" – 8 hex číslic (napr. "1A2B3C4D")
            return f"{volume_serial.value:08X}"
        return ""

    @staticmethod
    def get_current_drive_map() -> dict:
        """Vráti mapu {UUID: PísmenoDisku} pre všetky aktuálne pripojené disky."""
        import string
        from ctypes import windll

        drive_map = {}
        bitmask = windll.kernel32.GetLogicalDrives()
        
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:"
                uuid = DiskUUIDHelper.get_drive_uuid(drive)
                if uuid:
                    drive_map[uuid] = drive
            bitmask >>= 1
        return drive_map


# ========== LADIACI BLOK – po odladení zakomentujte ==========
#if __name__ == "__main__":
#    helper = DiskUUIDHelper()
#    print("UUID pre aktuálny adresár:", helper.get_drive_uuid(os.getcwd()))
#    print("Mapa všetkých diskov:", helper.get_current_drive_map())
#    import time
#    time.sleep(10)