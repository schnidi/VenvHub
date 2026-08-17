# VenvHub Pro - Release Notes (Changelog)

**Version:** v2.5.25  
*This document summarizes all security fixes, architectural enhancements to the APT system, thread management improvements, and localization updates introduced in version 2.5.25.*

---

## 🚀 New Features & Enhancements

### Intelligent Autoremove on Package Upgrade (Upgrade Lifecycle) [v2.5.25]
- **Proactive Dependency Capture:** Implemented advance capture of original package requirements (`Requires:`) in `AptListener` prior to executing the `--upgrade` command.
- **Automatic Orphan Cleanup Post-Update:** If a newer package version drops or reduces its dependencies (e.g., transitioning to modern standalone libraries), the system automatically identifies and cleanly removes newly orphaned dependencies using `autoremove`.

### Robust Venv Integrity Protection in UV Package Management [v2.5.25]
- **Strict Repair Outcome Evaluation:** `PipCommandWorker` now rigorously verifies the outcome of automated conflict resolution (`uv pip check` and auto-downgrade).
- **Prevention of False Success Signals:** If package installation succeeds but dependency conflict resolution fails, the worker emits an explicit failure code (`exit_code = 1`). This prevents premature generation of the virtual environment certificate (`BirthCertificateGenerator`) and prohibits unauthorized state persistence in the APT tracking registry.

### Defensive Qt Thread & Memory Management in Widgets [v2.5.25]
- **Concurrency Guard:** Implemented a safeguard in `windows/pip_package_widget.py` preventing repeated or programmatic invocations of `run_pip_command` while an existing thread is still active.
- **Automated Reference Cleanup:** Upon task completion, `self.thread` and `self.worker` references are immediately reset to `None`, eliminating memory leaks and dangling object references.

---

## 🐛 Bug Fixes & Stability

### PEP 503 Normalization in `get_requires_for_package` (Fix for Orphan Lock-in) [v2.5.25]
- **Critical Fix:** Unified package name normalization according to PEP 503 specifications (standardizing dots `.` and underscores `_` to hyphens `-`).
- **Impact:** Resolved a bug where released dependencies (e.g., `zope.interface` vs `zope-interface`) failed matching against the released dependency tree, which previously caused them to be falsely classified as manual installations by the Self-Healing mechanism.

### Safe Package Batch Processing (Chunking) in `get_dependency_graph` [v2.5.25]
- **Elimination of Destructive `continue` Statements:** Corrected chunked processing of packages in batches of 30 (`SHOW_MULTIPLE_CHUNK_SIZE`).
- **Impact:** If retrieving package metadata fails or times out for any chunk, the system immediately halts and returns an error state (`None`). This prevents the creation of partial dependency trees that could otherwise lead to the accidental uninstallation of active dependencies.

### Distinguishing Technical Failures from Empty Virtual Environments [v2.5.25]
- **Error Masking Resolution:** `get_dependency_graph()` now strictly returns `None` upon any technical error (e.g., inaccessible `python.exe`, corrupted `pip`, permission denial) and returns an empty dictionary `{}` exclusively for legitimate, newly initialized empty environments.
- **Impact on `autoremove` and `install_sync`:** In the event of a `pip list` failure, operations now abort immediately with a localized error message instead of reporting false success or triggering redundant mass reinstalls.

### Case-Insensitive Command Interception [v2.5.25]
- **Consistency Fix:** Fixed command detection in `apt_listener.py` to evaluate against `cmd_lower`, ensuring reliable tracking of manually installed packages regardless of character casing.

---

## 🌐 Localization & Translations (LanguageManager)

### 100% String Integration via `LanguageManager` [v2.5.25]
- All failure states, batch retrieval warnings, package listing errors, and UV diagnostic messages are now strictly routed through `LanguageManager.get()`.
- Added new localization keys to both **`sk_SK.json`** and **`en_US.json`**:
  - `apt_err_pkg_details_code`, `apt_err_pkg_details_fail`
  - `apt_err_pkg_list_code`, `apt_err_graph_failed`, `apt_err_graph`
  - `uv_fix_error_manual` (with parametric formatting for conflicting package lists).

---

## 📁 Modified & Affected Files

- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/button/pip/pip_command_worker.py`
- `windows/pip_package_widget.py`
- `/translations/sk_SK.json`
- `/translations/en_US.json`