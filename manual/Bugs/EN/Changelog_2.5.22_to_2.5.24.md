# VenvHub Pro - Consolidated Release Notes (Changelog)

**Version:** v2.5.24 (Cumulative Release from v2.5.22 to v2.5.24)  
*This document consolidates all architectural improvements, new features, security fixes, and bug fixes introduced across versions 2.5.23 and 2.5.24.*

---

## 🚀 New Features and Improvements

### Automatic Core Build Tools Injection (`setuptools` & `wheel`) [v2.5.24]
- **Self-Healing Venv Creation:** Updated `create.py` and `pip_installer.py` to automatically inject `setuptools` and `wheel` into every newly created virtual environment and repaired Python runtime.
- **Embedded Python Support:** Guaranteed that embedded and portable Python environments are fully equipped out of the box to build and install complex packages without requiring manual intervention.

### Multi-Level Path Normalization for Nested Requirements [v2.5.24]
- **Recursive File Discovery:** Implemented `PipManager._get_all_requirement_files()` to recursively scan and resolve all nested requirement files (e.g., `-r subfolder/requirements.txt`).
- **Complete Path Sanitization:** Integrated `PathNormalizer.sanitize_requirements_file()` across all discovered requirement files before initiating package installation. This guarantees cross-platform path slash compatibility (`/` vs `\`).

### Preserved Native Package Specifiers & Environment Markers [v2.5.24]
- **Full Pip/UV Feature Preservation:** Refactored requirement installation logic to preserve native version specifiers (`==`, `>=`), environment markers (`sys_platform`), extra index URLs, and direct editable links (`-e`) while eliminating path syntax errors.

### Clean Architecture & Single Responsibility Principle (APT System) [v2.5.23]
- **Structural Overhaul:** The APT dependency system underwent a major architectural cleanup. The `AptListener` was stripped of heavy logic and now acts strictly as an Interceptor (capturing actions).
- **Logic Migration:** All analytical methods (e.g., `_get_editable_packages`, `_is_package_required_by_others`, `_get_requires_for_package`) were moved to the core `AptLogic` module. The core logic analyzes data while the listener manages the UI flow.

### Dependency Injection & Inversion of Control (Container Logic) [v2.5.23]
- **Modern Design Pattern:** Implemented Dependency Injection in the `HookManager` (`hook.py`).
- **Dynamic Registration:** Instead of hardcoding dependencies, `HookManager` now allows external modules (such as `RespawnManager`) to dynamically register their crash-checking functions (`register_respawn_checker`), making container lifecycle management modular and testable.

---

## 🐛 Bug Fixes and Stability

### Security Fix for Path Traversal & Symlink Vulnerabilities in `RequirementsParser` [v2.5.24]
- **Root Entry Point Boundary Enforcement:** Fixed a critical security vulnerability in `RequirementsParser.parse()` where initial entry files (such as symlinks pointing to unauthorized files outside the project root) bypassed Path Traversal checks. Directory boundary validation is now strictly executed at the entry point for both primary and recursively nested (`-r`) requirement files.

### Fix for PEP 517 Build Backend Failures [v2.5.24]
- **Resolved `BackendUnavailable` Error:** Fixed the issue where installing local editable packages (`-e`) failed with `Cannot import 'setuptools.build_meta'`. Pre-installing `setuptools` and `wheel` into the environment ensures smooth PEP 517 builds.

### Fix for Windows/Linux Slash Mismatches in `-r` Flag [v2.5.24]
- **Path Parsing Fix:** Resolved errors where `pip install -r` crashed due to unescaped Windows backslashes or malformed relative paths inside nested requirements files.

### Embedded Python Environment Post-Processing [v2.5.24]
- **`EmbedPythonCreated` Service Enhancement:** Streamlined post-creation verification (`verify_pip_functional` & `fix_pth_file`) to ensure `._pth` files are unlocked and `site-packages` is immediately accessible.

### Resolved APT Circular Dependency Loop [v2.5.23]
- **Fix:** Completely eliminated a critical circular import loop between `apt_listener.py` and `apt_logic.py`.
- **Impact:** Prevents hidden `ImportError` crashes during application startup or background operations.

### Resolved Container Hook Circular Dependency Loop [v2.5.23]
- **Fix:** Broke an architectural loop between `hook.py` and `respawn_multi.py` in the container logic folder.
- **Impact:** `hook.py` no longer imports the Respawn Manager directly to check failure counts, ensuring seamless background terminal management.

---

## 🧹 Code Refactoring & Project Housekeeping

### Decoupled About Dialog (`AboutLogic` Service) [v2.5.24]
- **Eliminated Circular Dependencies:** Extracted multilingual HTML parsing and dialog initialization logic from `CustomTitleBar` into a dedicated `AboutLogic` service (`core/logic/sluzby/about_logic.py`).
- **Dynamic Registration:** Registered `AboutDialog` at startup in `main.py`, ensuring a clean architecture and preventing circular import risks.

### 100% Clean Architecture Validation [v2.5.23 - v2.5.24]
- Thanks to the removal of cyclical imports across APT logic, Container hooks, and UI services, the codebase passes strict architectural validation tests with **zero** detected circular dependency loops.

---

## 📁 Modified and Affected Files

- `core/logic/sluzby/requirements_parser.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/about_logic.py`
- `core/logic/sluzby/pip_installer.py`
- `core/logic/sluzby/create.py`
- `core/logic/containers/logic/hook.py`
- `core/logic/containers/logic/respawn_multi.py`
- `main.py`