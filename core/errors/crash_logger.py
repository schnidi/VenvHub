"""
Súbor: core/errors/crash_logger.py
Tento modul slúži na globálne zachytávanie neošetrených výnimiek ("tvrdých pádov") 
aplikácie, vrátane chýb v hlavnom vlákne, vedľajších vláknach a natívnych C/C++ pádoch pamäte.
"""

import os
import sys
import threading
import traceback
from datetime import datetime
from core._path import Paths

class CrashLogger:
    """
    Správca logovania kritických chýb a neočakávaných ukončení aplikácie.
    Nahrádza systémové handlery a faulthandler pre bezpečný zápis do súborov.
    """

    # Nízkoúrovňový OS súborový deskriptor (int) bez Python buffera.
    # Faulthandler pri natívnom páde (segfault/access violation) zapisuje
    # priamo cez OS syscall z C signal handlera, mimo Python interpretera,
    # takže je bezpečnejšie odovzdať mu surový fd namiesto Python file objektu.
    _fatal_fd = None

    @staticmethod
    def _write_crash_to_file(exc_type, exc_value, exc_traceback, thread_name="MainThread"):
        """
        Sformátuje výpis chyby (traceback) a zapíše ho do .log súboru 
        pomenovaného podľa aktuálneho dátumu.
        """
        error_dir = Paths.get_errors_dir()
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")

        log_file = os.path.join(error_dir, f"crash_{date_str}.log")

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_text = "".join(tb_lines)

        crash_msg = (
            f"\n{'='*60}\n"
            f"[{time_str}] KRITICKÝ PÁD APLIKÁCIE (Vlákno: {thread_name})\n"
            f"{'='*60}\n"
            f"{tb_text}\n"
        )

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(crash_msg)
                f.flush()
        except Exception as e:
            print(f"NEPODARILO SA ZAPÍSAŤ CRASH LOG: {e}")
            print(crash_msg)

    @staticmethod
    def handle_main_exception(exc_type, exc_value, exc_traceback):
        """
        Záchytný bod pre tvrdé pády A AJ sys.exit() volania v hlavnom vlákne.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Ak niekto zavolá sys.exit(), zapíšeme, kto a kde ho zavolal,
        # ale nezahlcujeme crash log falošnými poplachmi ako "kritický pád"
        if issubclass(exc_type, SystemExit):
            error_dir = Paths.get_errors_dir()
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")
            log_file = os.path.join(error_dir, f"crash_{date_str}.log")

            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            tb_text = "".join(tb_lines)

            exit_code = getattr(exc_value, 'code', 0)
            msg = (
                f"\n[{time_str}] VYVOLANÉ UKONČENIE APLIKÁCIE (sys.exit(kód={exit_code}))\n"
                f"Miesto volania na riadku:\n{tb_text}\n"
            )
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(msg)
                    f.flush()
            except Exception:
                pass
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        CrashLogger._write_crash_to_file(exc_type, exc_value, exc_traceback, thread_name="MainThread")
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    @staticmethod
    def handle_thread_exception(args):
        """
        Záchytný bod pre neošetrené výnimky vo vedľajších (pracovných) vláknach.
        """
        CrashLogger._write_crash_to_file(args.exc_type, args.exc_value, args.exc_traceback, thread_name=args.thread.name)

    @classmethod
    def setup(cls):
        """
        Aktivuje globálne odchytávanie prepísaním systémových hookov.
        Zároveň aktivuje faulthandler cez priamy OS deskriptor pre
        zaručený zápis pri natívnych C/C++ pádoch (segfault, access violation).
        """
        sys.excepthook = cls.handle_main_exception
        threading.excepthook = cls.handle_thread_exception

        import faulthandler
        error_dir = Paths.get_errors_dir()
        fatal_log = os.path.join(error_dir, "fatal_c_crashes.log")

        try:
            # Otvoríme súbor cez os.open (nízkoúrovňový OS zápis bez buffera)
            cls._fatal_fd = os.open(
                fatal_log,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0)
            )

            # Zapíšeme hlavičku priamo cez OS
            start_msg = f"\n--- ŠTART APLIKÁCIE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n".encode("utf-8")
            os.write(cls._fatal_fd, start_msg)

            # Bez all_threads=True pre zamedzenie Double Fault pádov:
            # prechádzanie stavu všetkých vlákien pri poškodenej pamäti
            # môže spôsobiť ďalší pád priamo v handleri a stratu logu.
            faulthandler.enable(file=cls._fatal_fd, all_threads=False)
        except Exception as e:
            print(f"Faulthandler chyba: {e}")
