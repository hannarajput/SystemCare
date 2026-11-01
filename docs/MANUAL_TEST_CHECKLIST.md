# SystemCare Manual Verification & QA Checklist

This checklist is designed for human testers verifying SystemCare releases on Windows 10 and Windows 11.

---

## Pre-Flight Setup
- [ ] Run `python --version` (confirm Python 3.10+ is installed).
- [ ] Install dependencies with `pip install -r requirements.txt`.
- [ ] Launch using `run.bat` or `python main.py`.

---

## 1. Overview Dashboard
- [ ] CPU usage updates smoothly in real time without spikes or UI stuttering.
- [ ] RAM usage displays percentage, used bytes, and available bytes accurately.
- [ ] Network I/O and Disk I/O indicators reflect real system activity.
- [ ] Thermal card displays reliable hardware temperature or cleanly indicates "Sensor driver unexposed to user-mode" if hardware sensors are restricted.
- [ ] Logical core distribution shows all logical processors (e.g. C1–C16) updating.
- [ ] Drive volume cards display valid free and used storage for all connected volumes.
- [ ] Clicking "Optimize System" navigates to the Safe Boost view.
- [ ] Clicking "View Health Details" navigates to the System Health view.

---

## 2. System Health Diagnosis
- [ ] Overall Health Score displays a calculated score (0–100) and status badge.
- [ ] Identified issues show category tags, summary, evidence, and clear recommendations.
- [ ] Healthy subsystems list displays verified normal aspects of the computer.
- [ ] Clicking "Run Check" re-evaluates the system and updates metrics without freezing.

---

## 3. Safe Boost Mode
- [ ] Displays live baseline RAM and CPU metrics.
- [ ] Action checklist lists available safe optimization tasks with safety ratings and estimated benefits.
- [ ] Clicking "Optimize Selected Items" shows progress feedback on the button.
- [ ] Results cards render: RAM Usage, Working Set Trimmed, Available RAM Delta, and Recycled/Freed Disk.
- [ ] Submitting multiple times in quick succession respects the 15-second cooldown timer.

---

## 4. Running Applications (Process Manager)
- [ ] List displays PID, process name, type, CPU %, Memory (MB), and username.
- [ ] System processes (such as `explorer.exe`, `dwm.exe`, `svchost.exe`) display "System (Protected)" and a disabled "Protected" label.
- [ ] User applications display a restrained red "End Task" button.
- [ ] Clicking "End Task" displays a confirmation dialog showing process name, PID, memory, and unsaved work warning.
- [ ] Filter segment toggle ("User Apps Only" vs "All Processes") filters rows accurately.
- [ ] Search entry filters by process name or PID instantly.

---

## 5. Startup Applications
- [ ] Displays startup applications from Registry (Run keys) and Windows Startup folders.
- [ ] Impact levels (Essential, High, Medium, Low) are visible.
- [ ] Essential security items display "Protected" and cannot be disabled.
- [ ] Toggling a user-level item displays a confirmation dialog and creates a safe registry backup.
- [ ] Segmented filter filters between All Items, User-Level, and System-Wide.

---

## 6. Duplicate File Finder
- [ ] Browsing to a directory loads the path correctly.
- [ ] Clicking "Scan for Duplicates" displays progress text and dynamic progress bar.
- [ ] Clicking "Cancel" stops the scan cleanly without crashing.
- [ ] Duplicate groups list file paths, sizes, and SHA-256 verification tags.
- [ ] Presets ("Keep Newest", "Keep Oldest", "Clear Selection") function accurately.
- [ ] Attempting to select all files in a group automatically preserves at least one copy and alerts the user.
- [ ] Clicking "Move Selected to Recycle Bin" displays confirmation and moves files to the Windows Recycle Bin.

---

## 7. Storage Analyzer
- [ ] Displays target folder path with a browse dialog.
- [ ] Minimum large file threshold can be selected (e.g. 20 MB, 50 MB, 100 MB).
- [ ] Cleanable temporary files section scans `%TEMP%`, crash dumps, and browser caches.
- [ ] Large files section lists files exceeding the threshold sorted largest first.
- [ ] Cleaning caches prompts for explicit confirmation and moves files to the Recycle Bin.

---

## 8. System Reports
- [ ] Renders a formatted audit overview with score, machine hostname, OS, and uptime.
- [ ] Lists recent optimization impact if Safe Boost was previously run.
- [ ] Clicking "Export as Markdown" saves a clean `.md` report to a user-chosen path.
- [ ] Clicking "Export as JSON" saves structured `.json` data to a user-chosen path.

---

## 9. Settings & Logs
- [ ] Switching color theme between Dark, Light, and System applies instantly across all controls.
- [ ] Refresh rate selector (1.0s, 1.5s, 2.0s, 3.0s) updates monitoring interval.
- [ ] In-app activity logs display recent operational entries with `%USERPROFILE%` sanitized.
- [ ] Clicking "Clear" resets the in-app log view.

---

## 10. General Quality & Desktop Feel
- [ ] Resizing the window scales layouts responsively without clipped text or overlapping controls.
- [ ] Closing the window cleanly terminates background worker threads without orphaned processes.

