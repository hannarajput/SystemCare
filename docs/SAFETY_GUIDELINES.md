# SystemCare Safety Guardrails & Principles

Safety is the highest design priority in SystemCare. This document explains the defensive boundaries, allowlists, and execution rules implemented throughout the codebase.

---

## 1. File Safety & Canonical Path Validation

All file paths are validated through `systemcare.utils.safety` before any read or destructive operation:

- **Canonical Path Resolution:** Paths are resolved with `canonicalize_path()`, expanding short 8.3 filenames, resolving symlinks, NTFS directory junctions, and evaluating relative path traversal (`..`).
- **Protected Windows Directories:** The OS strictly blocks operations targeting:
  - System Root (`C:\Windows`, `C:\Windows\System32`, `C:\Windows\SysWOW64`)
  - Program Files (`C:\Program Files`, `C:\Program Files (x86)`)
  - Volume Roots (`C:\`, `D:\`)
  - Swap, paging, and hibernation files (`pagefile.sys`, `swapfile.sys`, `hiberfil.sys`)
- **Protected Personal Libraries:** Every file and child directory inside user personal folders is strictly protected from cleanup:
  - `%USERPROFILE%\Documents`
  - `%USERPROFILE%\Desktop`
  - `%USERPROFILE%\Pictures`
  - `%USERPROFILE%\Videos`
  - `%USERPROFILE%\Music`
- **Explicit Cleanup Allowlisting:** Automatic cleaning routines are restricted to recognized scratch paths:
  - User Temporary Directory (`%LOCALAPPDATA%\Temp`)
  - Windows Crash Dumps (`%LOCALAPPDATA%\CrashDumps`)
  - Browser Media Caches (`Default\Cache\Cache_Data`)
- **No Unrecoverable Deletion:** The fallback to irreversible deletion (`os.remove`) has been completely removed. If the Windows Recycle Bin operation fails, the file is skipped and an error is logged.

---

## 2. Duplicate Detection & Copy Preservation

- **Three-Phase Verification:**
  1. Quick file size grouping.
  2. 4 KB block hashing for fast collision filtering.
  3. Full SHA-256 cryptographic verification across the entire byte stream.
- **Strict Group Preservation:** It is structurally impossible for SystemCare to delete all copies of a duplicate group. The engine enforces that at least one verified original is retained, even if a user manually selects all items.
- **Pre-Deletion Revalidation:** Immediately before sending a file to the Recycle Bin, the file's size and last modified timestamp are compared against the initial scan. If the file was edited or altered after scanning, deletion is aborted.

---

## 3. Windows Process Protection & PID Reuse Guard

- **Protected System Processes:** Core Windows executables (`ntoskrnl.exe`, `csrss.exe`, `svchost.exe`, `explorer.exe`, `dwm.exe`, `lsass.exe`, `services.exe`, `smss.exe`, `wininit.exe`) cannot be terminated by the application.
- **PID Reuse Verification:** Windows aggressively recycles Process IDs (PIDs). When a user confirms ending a task, `ProcessManager.terminate_process` checks:
  1. The PID is still active.
  2. The process image name matches the expected name.
  3. The process creation timestamp matches the expected creation time.
  If the operating system assigned the PID to a different application, termination is immediately cancelled.
- **Working Set Trimming vs. Available RAM:** Memory optimization invokes the Windows API `EmptyWorkingSet`. This signals the Windows memory manager to transition idle pages to the standby list without terminating processes or modifying page files.

---

## 4. Startup Application Safety

- **Non-Destructive Registry Backups:** Modifying startup entries writes a backup copy to a safe configuration key.
- **Rollback Guarantee:** If a registry write operation fails midway, the previous state is restored atomically.
- **Guarded System Services:** Essential startup entries (such as Windows Security Health Systray) cannot be disabled.

---

## 5. Local Privacy

- **Path Redaction in Logs:** Any reference to `%USERPROFILE%` in console logs, UI logs, or disk log files is redacted to `%USERPROFILE%` to protect user usernames and file paths.
- **No Network Requests:** The application contains zero outbound network clients, sockets, or HTTP requests.

