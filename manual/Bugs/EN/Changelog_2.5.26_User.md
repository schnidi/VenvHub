# VenvHub Pro - Release Notes (Changelog)

**Version:** v2.5.26  
*This update brings automatic cleanup of unused libraries after bulk updates, protection against accidental uninstallation of packages from requirements.txt, full integration for local editable packages (pip -e), and background stability improvements.*

---

## 🚀 New Improvements

### 🧹 Bulk Autoremove Cleanup
- **Clean environment after every update:** When you click the **Update All** button (whether in the Pip Manager window, the main Manager window, or via the lightning bolt icon in the table), the application automatically scans the entire system after successfully updating packages.
- **Removal of leftover helper libraries:** All obsolete and unused dependencies (orphans) that are no longer required by newer package versions are automatically and safely uninstalled right after the bulk update.
- **Consistent behavior:** All bulk update methods across the entire application now guarantee the same optimal, clean environment state.

### ⚠️ Protection and Warnings for Core Packages (`requirements.txt`)
- **Smart warning dialog:** If you attempt to uninstall a package that is explicitly defined in the project's `requirements.txt` file, the application displays a prominent warning informing you that the environment will no longer match the project definition.
- **Three-tier protection:** The application reliably distinguishes between standalone packages, protected sub-dependencies (which cannot be deleted while required by another package), and core project packages.
- **Full localization:** Dialog windows and messages are fully translated into both Slovak and English.

### ✏️ Full Integration for Local Editable Packages (`pip -e`)
- **Automated dependency management:** Development packages installed from local folders in editable mode are now fully registered within the intelligent APT system.
- **Post-uninstall cleanup:** When uninstalling an editable package (either from the *Local Packages* window or the regular *Pip Manager*), autoremove is automatically triggered to safely clean up all orphaned libraries that the package relied on.

### 🛠️ Bug Fixes and Stability Improvements
- **Reliable background tasks:** Fixed a memory signal-dropping issue (Garbage Collector bug) that could, under certain conditions, cause automatic post-uninstall cleanup to be silently skipped.
- **Accurate package tracking:** Package upgrades no longer artificially mark sub-dependencies as "manually installed," ensuring the system always accurately knows which dependencies are safe to clean up in the future.

---

## 📁 Modified Files

- `core/logic/sluzby/apt_listener.py`
- `core/logic/sluzby/apt_logic.py`
- `windows/pip_package_widget.py`
- `translations/sk_SK.json`
- `translations/en_US.json`