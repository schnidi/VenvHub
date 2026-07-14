#----------------------------------------
# Súbor: core/logic/path_logic/disk_uuid_win_lin.py
#----------------------------------------

import os
import sys
import platform
import json

# ---------- WINDOWS ----------
def get_disk_info_windows():
    """Získa info o všetkých logických diskoch (C:, D:, ...) – rýchle, len API."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    drives = []
    bitmask = kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive = f"{letter}:\\"

            # UUID (Volume Serial Number)
            serial = wintypes.DWORD()
            fs_name = ctypes.create_unicode_buffer(256)
            vol_name = ctypes.create_unicode_buffer(256)
            success = kernel32.GetVolumeInformationW(
                drive, vol_name, 256, ctypes.byref(serial), None, None,
                fs_name, 256
            )
            if not success:
                # Prázdna jednotka (CD, odpojená sieťovka) – preskočiť
                bitmask >>= 1
                continue

            uuid = f"{serial.value:08X}" if serial.value else ""
            fs_type = fs_name.value

            # Celková a voľná veľkosť
            free_avail = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            free_total = ctypes.c_ulonglong(0)
            kernel32.GetDiskFreeSpaceExW(
                drive,
                ctypes.byref(free_avail),
                ctypes.byref(total_bytes),
                ctypes.byref(free_total)
            )
            total_gb = total_bytes.value / (1024 ** 3)
            free_gb = free_avail.value / (1024 ** 3)

            drives.append({
                "mount": f"{letter}:",
                "uuid": uuid,
                "filesystem": fs_type,
                "total_gb": round(total_gb, 2),
                "free_gb": round(free_gb, 2)
            })
        bitmask >>= 1
    return drives

# ---------- LINUX ----------
def get_disk_info_linux():
    """Získa info o všetkých pripojených diskoch (mount pointoch)."""
    mounts = []
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 6:
                    continue
                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                # Preskoč nepodstatné
                if any(x in mountpoint for x in ['/dev', '/proc', '/sys', '/run', '/snap', '/var/lib/docker']):
                    continue
                if not device.startswith('/dev/'):
                    continue
                if device.startswith('/dev/loop'):
                    continue

                # UUID z /dev/disk/by-uuid/
                uuid = get_uuid_linux(device)

                # Veľkosť (celková, voľná)
                try:
                    stat = os.statvfs(mountpoint)
                    total_bytes = stat.f_blocks * stat.f_frsize
                    free_bytes = stat.f_bavail * stat.f_frsize
                    total_gb = total_bytes / (1024 ** 3)
                    free_gb = free_bytes / (1024 ** 3)
                except OSError:
                    total_gb, free_gb = 0.0, 0.0

                mounts.append({
                    "mount": mountpoint,
                    "uuid": uuid,
                    "filesystem": fstype,
                    "total_gb": round(total_gb, 2),
                    "free_gb": round(free_gb, 2)
                })
    except FileNotFoundError:
        pass
    return mounts

def get_uuid_linux(device):
    try:
        base = os.path.basename(device)
        for entry in os.scandir('/dev/disk/by-uuid/'):
            target = os.readlink(entry.path)
            if target == device or target == base or target == os.path.join('..', '..', device):
                return entry.name
    except (FileNotFoundError, OSError):
        pass
    return ""


# ---------- HLAVNÉ ROZHRANIE PRE ZVYŠOK APLIKÁCIE ----------
def get_all_disks_info() -> list:
    """
    Univerzálna funkcia na získanie dát bez ohľadu na OS.
    Vráti zoznam slovníkov s údajmi o každom disku/partícii.
    """
    system = platform.system()
    if system == "Windows":
        return get_disk_info_windows()
    elif system == "Linux":
        return get_disk_info_linux()
    else:
        return []


# ---------- TESTOVACÍ BLOK ----------
# Zmeňte na 'y' ak chcete skript spustiť samostatne a vidieť výstup v konzole
RUN_TEST = 'n'

def _test_main():
    data = get_all_disks_info()
    if not data:
        print(json.dumps({"error": f"Nepodporovaný systém: {platform.system()}"}))
        sys.exit(1)

    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    if RUN_TEST.lower() == 'y':
        _test_main()