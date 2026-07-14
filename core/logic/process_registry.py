#----------------------------------------
# Súbor: core/logic/process_registry.py
#----------------------------------------
import psutil
import os
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal, Qt

from core.logic.language_manager import LanguageManager


class _RegistryNotifier(QObject):
    """Most pre doručenie watchdog signálov na hlavné Qt vlákno."""
    update_signal = pyqtSignal(int, str, str, str)


class ProcessWatchdog:
    """
    Inteligentný watchdog, ktorý sa nenechá oklamať pretekom vlákien.
    Presne vie, či proces spadol, alebo ho zámerne zastavil užívateľ.
    """
    @staticmethod
    def watch(registry_instance, pid, key_name, process_type):
        def _monitor():
            def was_stopped_by_user():
                with registry_instance._lock:
                    return key_name in registry_instance._intentionally_stopped

            try:
                if was_stopped_by_user(): return
                
                if not psutil.pid_exists(pid):
                    if not was_stopped_by_user():
                        msg = LanguageManager.get('watchdog_process_not_started', 'Proces sa nepodarilo spustiť')
                        out_msg = f"\n[WATCHDOG] 🚨 {msg} (Skript: '{key_name}')"
                        registry_instance._notify(pid, key_name, 'ERROR_NOT_STARTED', out_msg)
                    return

                parent = psutil.Process(pid)
                target_proc = parent

                if process_type == 'terminal':
                    found = False
                    for _ in range(6):
                        if was_stopped_by_user(): return
                        try:
                            for child in parent.children(recursive=True):
                                if 'python' in child.name().lower():
                                    target_proc = child
                                    found = True
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        
                        if found: break 
                        time.sleep(0.5) 
                    
                    if not found:
                        if not was_stopped_by_user():
                            msg = LanguageManager.get('watchdog_script_crashed_on_start', 'Skript zlyhal hneď po štarte (okno sa okamžite zatvorilo)')
                            out_msg = f"\n[WATCHDOG] 🚨 {msg} (Chyba v: '{key_name}')"
                            registry_instance._notify(pid, key_name, 'ERROR_CRASHED_START', out_msg)
                        return

                # --- HLAVNÉ IN-TIME SLEDOVANIE ---
                while True:
                    if was_stopped_by_user(): return
                    
                    try:
                        if not target_proc.is_running(): break
                    except psutil.NoSuchProcess:
                        break
                        
                    time.sleep(0.5)
                    
                if not was_stopped_by_user():
                    msg = LanguageManager.get('watchdog_script_crashed_in_time', 'Bežiaci skript neočakávane spadol')
                    out_msg = f"\n[WATCHDOG] 🚨 {msg} (Skript: '{key_name}')"
                    registry_instance._notify(pid, key_name, 'ERROR_CRASHED', out_msg)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                if not was_stopped_by_user():
                    msg = LanguageManager.get('watchdog_process_crashed', 'Proces programu neočakávane zanikol')
                    out_msg = f"\n[WATCHDOG] 🚨 {msg} (Skript: '{key_name}')"
                    registry_instance._notify(pid, key_name, 'ERROR_CRASHED', out_msg)
            except Exception:
                pass 

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()


class ProcessRegistry:
    def __init__(self):
        self._registry = {}
        self._intentionally_stopped = set()
        self._callback = None
        self._lock = threading.Lock()
        self._notifier = None
        self._job_handle = None
        if os.name == 'nt':
            try:
                self._init_job_object()
            except Exception as e:
                print(LanguageManager.get("registry_err_job_init", "ERROR [Registry]: Failed to initialize Windows Job Object: {error}").format(error=e))

    def _init_job_object(self):
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('ReadOperationCount', ctypes.c_uint64),
                ('WriteOperationCount', ctypes.c_uint64),
                ('OtherOperationCount', ctypes.c_uint64),
                ('ReadTransferCount', ctypes.c_uint64),
                ('WriteTransferCount', ctypes.c_uint64),
                ('OtherTransferCount', ctypes.c_uint64),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('PerProcessUserTimeLimit', ctypes.c_int64),
                ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD),
                ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t),
                ('PriorityClass', wintypes.DWORD),
                ('SchedulingClass', wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t),
                ('PeakJobMemoryUsed', ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        self._job_handle = kernel32.CreateJobObjectW(None, None)
        if not self._job_handle:
            raise ctypes.WinError(ctypes.get_last_error())

        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

        size = ctypes.sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)
        res = kernel32.SetInformationJobObject(
            self._job_handle,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(limits),
            size
        )
        if not res:
            kernel32.CloseHandle(self._job_handle)
            self._job_handle = None
            raise ctypes.WinError(ctypes.get_last_error())
        print(LanguageManager.get("registry_log_job_ok", "DEBUG [Registry]: Windows Job Object successfully initialized and configured."))

    def _ensure_notifier(self):
        if self._notifier is None:
            self._notifier = _RegistryNotifier()
            self._notifier.update_signal.connect(
                self._invoke_callback,
                Qt.ConnectionType.QueuedConnection
            )

    def _invoke_callback(self, pid, key_name, status, message):
        if self._callback:
            self._callback(pid, key_name, status, message)

    def set_callback(self, callback_func):
        """
        Zaregistruje externú funkciu z iného súboru (napr. GUI).
        Callback sa vždy volá na hlavnom Qt vlákne.
        """
        self._callback = callback_func
        if callback_func:
            self._ensure_notifier()

    def _notify(self, pid, key_name, status, message):
        """
        Odovzdá dáta do callbacku. Ak ešte nie je priradený,
        vypíše klasický log do konzoly.
        """
        if self._callback:
            self._ensure_notifier()
            if self._notifier is not None:
                self._notifier.update_signal.emit(pid, key_name, status, message)
        else:
            print(message)

    def get_pids(self, key):
        """Vráti kópiu množiny PID pre daný venv kľúč."""
        if not key:
            return set()
        normalized_key = os.path.normpath(key).lower()
        with self._lock:
            entry = self._registry.get(normalized_key, {})
            return entry.get('pids', set()).copy()

    def register(self, key, pid, process_type):
        if not key or not pid or not process_type: return
        normalized_key = os.path.normpath(key).lower()

        with self._lock:
            self._intentionally_stopped.discard(normalized_key)

            if normalized_key not in self._registry:
                self._registry[normalized_key] = {'type': process_type, 'pids': set(), 'handles': {}}
            elif 'handles' not in self._registry[normalized_key]:
                self._registry[normalized_key]['handles'] = {}
            
            self._registry[normalized_key]['pids'].add(pid)

            # Open Windows handle and assign to Job Object
            if os.name == 'nt' and self._job_handle:
                try:
                    import ctypes
                    # PROCESS_SET_QUOTA = 0x0100, PROCESS_TERMINATE = 0x0001, SYNCHRONIZE = 0x00100000, PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    access = 0x0100 | 0x0001 | 0x00100000 | 0x1000
                    h_proc = ctypes.windll.kernel32.OpenProcess(access, False, pid)
                    if h_proc:
                        self._registry[normalized_key]['handles'][pid] = h_proc
                        # Assign to Job Object
                        res = ctypes.windll.kernel32.AssignProcessToJobObject(self._job_handle, h_proc)
                        if res:
                            print(LanguageManager.get("registry_log_job_assign_ok", "DEBUG [Registry]: Assigned PID {pid} to Job Object.").format(pid=pid))
                        else:
                            print(LanguageManager.get("registry_log_job_assign_err", "DEBUG [Registry]: Failed to assign PID {pid} to Job Object: {error}").format(pid=pid, error=ctypes.WinError()))
                    else:
                        print(LanguageManager.get("registry_log_job_handle_err", "DEBUG [Registry]: Failed to open handle for PID {pid}: {error}").format(pid=pid, error=ctypes.WinError()))
                except Exception as e:
                    print(LanguageManager.get("registry_log_job_critical", "DEBUG [Registry]: Error opening handle/assigning to Job: {error}").format(error=e))
        
        out_msg = LanguageManager.get("registry_log_registered", "DEBUG [Registry]: Registered PID {pid} (type: {type}) for key '{key}'").format(pid=pid, type=process_type, key=normalized_key)
        self._notify(pid, normalized_key, 'RUNNING', out_msg)

        ProcessWatchdog.watch(self, pid, normalized_key, process_type)

    def is_running(self, key):
        if not key: return False
        normalized_key = os.path.normpath(key).lower()
        
        with self._lock:
            if normalized_key not in self._registry: return False
            
            entry = self._registry[normalized_key]
            if not entry.get('pids'): return False

            process_type = entry['type']
            pids_to_check = entry['pids'].copy()
        
        for pid in pids_to_check:
            try:
                if not psutil.pid_exists(pid):
                    with self._lock:
                        if normalized_key in self._registry:
                            self._registry[normalized_key]['pids'].discard(pid)
                            handles = self._registry[normalized_key].get('handles', {})
                            if pid in handles:
                                h_proc = handles.pop(pid)
                                if os.name == 'nt':
                                    try:
                                        import ctypes
                                        ctypes.windll.kernel32.CloseHandle(h_proc)
                                    except Exception:
                                        pass
                    continue
                
                parent = psutil.Process(pid)
                
                if process_type == 'terminal':
                    if any('python' in p.name().lower() for p in parent.children(recursive=True)):
                        return True
                
                elif process_type == 'silent':
                    if 'python' in parent.name().lower():
                        return True
            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                with self._lock:
                    if normalized_key in self._registry:
                        self._registry[normalized_key]['pids'].discard(pid)
                        handles = self._registry[normalized_key].get('handles', {})
                        if pid in handles:
                            h_proc = handles.pop(pid)
                            if os.name == 'nt':
                                try:
                                    import ctypes
                                    ctypes.windll.kernel32.CloseHandle(h_proc)
                                except Exception:
                                    pass
                continue
        
        return False

    def cleanup_dead_processes(self, key):
        if not key: return
        normalized_key = os.path.normpath(key).lower()
        
        with self._lock:
            if normalized_key not in self._registry: return

            entry = self._registry[normalized_key]
            pids_to_remove = set()
            for pid in entry['pids'].copy():
                try:
                    if not psutil.Process(pid).is_running():
                        pids_to_remove.add(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pids_to_remove.add(pid)

            entry['pids'].difference_update(pids_to_remove)
            
            handles = entry.get('handles', {})
            for pid in pids_to_remove:
                if pid in handles:
                    h_proc = handles.pop(pid)
                    if os.name == 'nt':
                        try:
                            import ctypes
                            ctypes.windll.kernel32.CloseHandle(h_proc)
                        except Exception:
                            pass

    def kill_and_unregister(self, key):
        if not key: return
        normalized_key = os.path.normpath(key).lower()

        with self._lock:
            if normalized_key not in self._registry: return

            self._intentionally_stopped.add(normalized_key)

            entry = self._registry.get(normalized_key, {})
            pids_to_kill = entry.get('pids', set()).copy()
            handles = entry.get('handles', {}).copy()
            
            if normalized_key in self._registry:
                del self._registry[normalized_key]
            
        for pid in pids_to_kill:
            try:
                if psutil.pid_exists(pid):
                    parent = psutil.Process(pid)
                    for child in parent.children(recursive=True): child.kill()
                    parent.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            if pid in handles:
                h_proc = handles[pid]
                if os.name == 'nt':
                    try:
                        import ctypes
                        ctypes.windll.kernel32.CloseHandle(h_proc)
                    except Exception:
                        pass
            
            self._notify(pid, normalized_key, 'STOPPED', LanguageManager.get("registry_log_stopped", "DEBUG [Registry]: Stopped PID {pid}").format(pid=pid))
        
        print(LanguageManager.get("registry_log_unregistered", "DEBUG [Registry]: Unregistered and killed all for key '{key}'").format(key=normalized_key))

process_registry = ProcessRegistry()