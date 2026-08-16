# VenvHub Pro - Consolidated Release Notes (Changelog)

**Version:** v2.5.25  
*This document summarizes all architectural enhancements, performance optimizations, bug fixes, and stability improvements introduced in version 2.5.25.*

---

## 🚀 New Features and Stability Improvements

### 1. Full Dependency Management Compatibility with PEP 503 [v2.5.25]
- **Accurate Package Normalization:** The package management mechanism (APT logic) was updated to strictly comply with the PEP 503 standard. Package names containing dots (`.`) or underscores (`_`) (e.g., `zope.interface`, `backports.zoneinfo`) are now properly normalized in the internal graph.
- **Flawless Orphan Management:** Thanks to unified normalization, released dependencies are no longer mistakenly locked, and the intelligent cleanup function (`autoremove`) operates with maximum precision.

### 2. Enhanced Integrity and Safety in Dependency Analysis [v2.5.25]
- **Protection Against Incomplete Data (Fail-Safe Dependency Graph):** An atomic approach was introduced when querying the state of installed packages. If the process of fetching package information fails or is interrupted, the system safely halts the operation rather than operating on an incomplete list.
- **Prevention of Accidental Deletion:** This eliminates the risk of the automatic cleanup function (`autoremove`) mistakenly identifying a required library as an orphan due to a transient read error.
- **Fail-Safe Pre-Uninstall Check:** The same principle was extended to the reverse dependency check executed immediately before package uninstallation. If the environment state cannot be reliably determined at that moment, the operation is safely aborted and the user is informed, preventing silent uninstallation without verification.

### 3. Improved Cleanup of Obsolete Libraries During Package Upgrades [v2.5.25]
- **Accurate Lifecycle Tracking:** During `pip install --upgrade` (or `-U`) operations, the system captures the dependency tree of the original package version before the installation of the new version begins.
- **Immediate Release of Unneeded Dependencies:** If the new package version no longer requires certain older supporting libraries, the system correctly identifies them and enables their automatic cleanup.

### 4. Refined Result Indication for UV Installations [v2.5.25]
- **More Accurate Feedback:** Improved integration and reporting with the ultra-fast UV (Astral) installer. If a post-installation dependency check discovers a conflict that cannot be resolved automatically, the application accurately reports the status and prevents writing an incorrect environment state.

---

## 🐛 Bug Fixes and System Patches

### Package Name Inconsistencies Fix During Dependency Parsing
- **Description:** Eliminated discrepancies between raw package manager text output and normalized keys in the dependency graph, which previously caused some packages not to be removed after their parent library was uninstalled.
- **Solution:** All extracted dependencies now undergo strict PEP 503 normalization.

### Error Handling During Package List Retrieval
- **Description:** In the event of a system command failure while listing packages, the application incorrectly assumed the virtual environment was empty and reported a successful operation.
- **Solution:** Error states are now explicitly distinguished from an empty environment, and users are notified of the actual failure.

### Prevention of Incomplete Dependency Graphs
- **Description:** If reading details for a single package group failed, a partial graph missing critical connections could be generated.
- **Solution:** Any error encountered during package metadata collection now immediately and safely aborts the analysis.

### Unified Case Sensitivity in Installed Package Detection
- **Description:** When processing an install/upgrade command, part of the logic (detecting whether it is an installation) was evaluated case-insensitively, while extracting the list of installed packages from the same command was case-sensitive. Under unusual command casing, a package could remain unmarked as explicit.
- **Solution:** Extracting the list of installed packages now uses the same case-insensitive evaluation as the rest of the command detection logic.

### Capturing Released Dependencies Prior to Upgrade
- **Description:** When upgrading a package to a newer version, old dependencies were previously checked only after files were overwritten on disk, at which point the original requirements could no longer be inspected.
- **Solution:** Analysis of original requirements now occurs in advance.

### Exit Code Correction on UV Dependency Check Failure
- **Description:** In certain cases, the UV installer reported success even when the automatic remediation of detected conflicts failed.
- **Solution:** The final exit status of the installation task now reflects the outcome of the compatibility remediation phase.

### Fail-Safe Behavior for Reverse Dependency Checks Prior to Uninstall
- **Description:** The check verifying whether a package is required by any other installed package would silently treat a transient environment inspection failure as if "no package requires it" — allowing uninstallation to proceed without real verification.
- **Solution:** Environment inspection failures are now strictly differentiated from a confirmed "no dependencies required" state. In case of uncertainty, uninstallation is blocked and the user is informed that verification failed and to try again.

### Safe Thread Termination for Overlapping Pip Operations
- **Description:** The pip operation completion handler resolved the running thread reference only when it finished. If two operations overlapped on the same package panel (e.g., by bypassing UI locks), it could accidentally wait for or terminate a newer, still-running thread belonging to another operation instead of its own.
- **Solution:** The specific thread reference is now captured upon operation start and passed explicitly to the completion handler, ensuring it always manages its own thread regardless of the panel's shared state.

---

## 🌐 Localization

- Added a new translation key `apt_err_cannot_verify_deps` (both EN and SK) for the pre-uninstall safety check — informing the user that dependency verification failed and the operation was aborted for safety reasons.

---

## 📁 Affected Core Application Files

- `core/logic/sluzby/apt_logic.py`
- `core/logic/sluzby/apt_listener.py`
- `core/logic/button/pip/pip_command_worker.py`
- `windows/pip_package_widget.py`