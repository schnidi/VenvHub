# VenvHub Pro - Release Notes (Changelog)
**Version:** v2.5.23 (Jump from version v2.5.22)

This document summarizes all differences, architectural improvements, and bug fixes between versions 2.5.22 and 2.5.23.

### 🚀 New Features and Improvements

**Clean Architecture & Single Responsibility Principle (APT System)**
* **Structural Overhaul:** The APT dependency system underwent a major architectural cleanup. The `AptListener` was stripped of all heavy logic and is now acting strictly as an Interceptor (an invisible bridge capturing actions).
* **Logic Migration:** All analytical methods (e.g., `_get_editable_packages`, `_is_package_required_by_others`, `_get_requires_for_package`) were moved to the core `AptLogic` module. The "brain" now analyzes the data, while the "listener" only handles the UI flow. 

**Dependency Injection & Inversion of Control (Container Logic)**
* **Modern Design Pattern:** Implemented Dependency Injection in the `HookManager` (`hook.py`). 
* **Dynamic Registration:** Instead of hardcoding dependencies, the `HookManager` now allows external modules (like `RespawnManager`) to dynamically register their crash-checking functions (`register_respawn_checker`). This makes the container lifecycle management highly modular and much easier to test.

### 🐛 Bug Fixes and Stability

**Resolved APT Circular Dependency Loop**
* **Fix:** Completely eliminated a critical circular dependency (Circular Import Loop) between `apt_listener.py` and `apt_logic.py`. 
* **Impact:** Prevents hidden `ImportError` crashes during application startup or when triggering background operations. The system is now significantly more stable and linter-compliant.

**Resolved Container Hook Circular Dependency Loop**
* **Fix:** Broken an architectural loop between `hook.py` and `respawn_multi.py` in the container logic folder.
* **Impact:** `hook.py` no longer needs to import the Respawn Manager to check if a process failed 3 times. This eliminates silent risks during the starting sequence of multiple environments and ensures seamless background terminal management.

**100% Clean Architecture Validation**
* Thanks to the aggressive removal of cyclical imports, the project now successfully passes strict architectural validation tests with **zero** detected circular dependency loops. The codebase is now highly robust and ready for future scaling.

### 📁 Modified Files
* `core/logic/sluzby/apt_listener.py`
* `core/logic/sluzby/apt_logic.py`
* `core/logic/containers/logic/hook.py`
* `core/logic/containers/logic/respawn_multi.py`