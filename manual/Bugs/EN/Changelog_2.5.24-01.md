# VenvHub Pro - Release Notes (Changelog)

**Version:** v2.5.24 (Jump from version v2.5.23)  
*This document summarizes all differences, new features, and bug fixes introduced in version 2.5.24.*

---

## 🚀 New Features and Improvements

### Automatic Core Build Tools Injection (`setuptools` & `wheel`)
- **Self-Healing Venv Creation:** Updated `create.py` and `pip_installer.py` to automatically inject `setuptools` and `wheel` into every newly created virtual environment and repaired Python runtime.
- **Embedded Python Support:** Guaranteed that embedded and portable Python environments are fully equipped out of the box to build and install complex packages without requiring manual intervention.

### Multi-Level Path Normalization for Nested Requirements
- **Recursive File Discovery:** Implemented `PipManager._get_all_requirement_files()` to recursively scan and resolve all nested requirement files (e.g., `-r subfolder/requirements.txt`).
- **Complete Path Sanitization:** Integrated `PathNormalizer.sanitize_requirements_file()` across all discovered requirement files before initiating package installation. This guarantees cross-platform path slash compatibility (`/` vs `\`).

### Preserved Native Package Specifiers & Environment Markers
- **Full Pip/UV Feature Preservation:** Refactored requirement installation logic to preserve native version specifiers (`==`, `>=`), environment markers (`sys_platform`), extra index URLs, and direct editable links (`-e`) while eliminating path syntax errors.

---

## 🐛 Bug Fixes and Stability

### Fix for PEP 517 Build Backend Failures
- **Resolved `BackendUnavailable` Error:** Fixed the critical issue where installing local editable packages (`-e`) failed with `Cannot import 'setuptools.build_meta'`. Pre-installing `setuptools` and `wheel` into the environment ensures smooth PEP 517 builds.

### Fix for Windows/Linux Slash Mismatches in `-r` Flag
- **Path Parsing Fix:** Resolved errors where `pip install -r` crashed due to unescaped Windows backslashes or malformed relative paths inside nested requirements files.

### Embedded Python Environment Post-Processing
- **`EmbedPythonCreated` Service Enhancement:** Streamlined post-creation verification (`verify_pip_functional` & `fix_pth_file`) to ensure `._pth` files are unlocked and `site-packages` is immediately accessible.

---

## 🧹 Code Refactoring & Project Housekeeping

### Decoupled About Dialog (`AboutLogic` Service)
- **Eliminated Circular Dependencies:** Extracted multilingual HTML parsing and dialog initialization logic from `CustomTitleBar` into a new dedicated `AboutLogic` service (`core/logic/sluzby/about_logic.py`).
- **Dynamic Registration:** Registered `AboutDialog` at startup in `main.py`, ensuring a clean architecture and preventing circular import risks when opening the About window.

