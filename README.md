# SystemCare — PC Health & Performance Optimizer

**SystemCare** is a clean, minimal, professional Windows desktop application engineered with **Python**, **CustomTkinter**, and **psutil**. Designed with the simplicity and restrained aesthetics of Windows 11 Settings and Microsoft PowerToys, it delivers real-time hardware telemetry, performance diagnostics, background application review, startup inspection, duplicate file detection, storage analysis, and genuine system optimization.

---

## Visual Design & Architecture

SystemCare is designed as a genuine, trustworthy Windows desktop utility:
- **Restrained Professional Palette:** Soft charcoal in dark mode (`#1a1c20`, `#22252a`), clean white/neutral gray in light mode (`#ffffff`, `#f8f9fa`), subtle borders (`1px`), and muted accent blue (`#0066cc` / `#2563eb`).
- **Native Typography:** Standardized on native Windows Segoe UI with consistent scale (Main headings 20px, section titles 15–16px, body 13px, metrics 26px).
- **Usability Over Decoration:** Zero flashy animations, neon glow, or excessive badges. Clear visual hierarchy with predictable feedback.
- **Minimal Monochrome Navigation:** Consistent symbol glyphs (`⊞`, `♥`, `⚡`, `≡`, `▶`, `⧉`, `⛁`, `📋`, `⚙`) with subtle active-state highlighting.

---

## 🌟 Core Features

### 1. ⊞ Overview (Live System Monitor)
- **Real-Time Telemetry:** Continuous sampling of CPU utilization (overall % and per-core distribution), memory (used, free, swap), storage volumes, network transfer rates, and disk I/O rates.
- **Hardware Temperature Protection:** Directly probes hardware sensors. When sensor diodes are unexposed to user-mode without kernel drivers, the app gracefully reports `"Unavailable — Sensor driver unexposed to user-mode"`, avoiding fabricated statistics.
- **Lightweight Architecture:** Background worker thread polls metrics at configurable intervals (1.0s – 3.0s) with negligible CPU footprint (<0.5%).

### 2. ♥ System Health (Performance Diagnosis)
- **Evidence-Based Diagnostic Heuristics:** Analyzes system metrics against validated hardware thresholds.
- **Identifies & Explains:**
  - High CPU utilization and runaway processes.
  - Memory pressure, low available RAM headroom, and swap paging thrashing.
  - Storage volume constraints (<15% free or <10 GB remaining).
  - Thermal risks and sustained CPU load factors.
- **Direct Language & Evidence:** Every detected issue includes a clear summary, observed telemetry evidence, and an actionable recommendation.

### 3. ⚡ Safe Boost (System Optimization)
- **Transparent & Grounded:** Never promises artificial speedups, disables core Windows security services, or alters critical registry hives.
- **Selectable Optimization Checklist:**
  - *Trim Idle Process Working Sets:* Calls the official Windows Memory Manager API (`EmptyWorkingSet` via `psapi.dll`) on idle applications to transition unreferenced pages back to available standby RAM.
  - *Clean User Temporary Files:* Purges discarded scratch files from `%TEMP%`.
  - *Clean Application Crash Dumps:* Clears old diagnostic error dumps.
  - *Flush Browser Web Caches:* Reclaims temporary web asset storage.
- **Evidence-Based Telemetry:** Accurately distinguishes working sets trimmed, change in available physical RAM, files recycled, and physical disk space freed. Includes a 15-second rate-limiting cooldown.

### 4. ≡ Running Applications (Process Manager)
- **Process Enumeration:** Lists active applications with PID, name, type, CPU %, memory usage (MB), and username.
- **Search & Filter:** Search by name or PID; filter between "User Apps Only" and "All Processes".
- **Strict System Process Whitelist:** Essential Windows processes (`System`, `svchost.exe`, `explorer.exe`, `dwm.exe`, `csrss.exe`, `services.exe`, `lsass.exe`, PID 0, PID 4, etc.) are permanently locked.
- **PID Reuse Protection:** Compares process name and process creation timestamp before termination to prevent terminating re-assigned PIDs.

### 5. ▶ Startup Applications (Startup Manager)
- **Multi-Location Discovery:** Scans startup applications across Registry User (`HKCU\Run`), Registry System (`HKLM\Run`), and Windows Startup folders (`%APPDATA%` and `%PROGRAMDATA%`).
- **Impact Ratings & Guidance:** Categorizes items by impact (`Essential`, `High`, `Medium`, `Low`) with clear advice on whether disabling is beneficial.
- **Safe Toggle with Atomic Rollback:** Non-essential startup items can be toggled with explicit confirmation. Disabled registry items are preserved under `HKCU\Software\SystemCare\DisabledStartup` for instant rollback.

### 6. ⧉ Duplicate Files (Duplicate Finder)
- **Staged Cryptographic Verification:**
  - *Phase 1:* File size grouping (discards 95%+ unique files instantly).
  - *Phase 2:* 4 KB header hashing on colliding file sizes.
  - *Phase 3:* Full SHA-256 calculation for byte-exact verification.
- **Strict Group Preservation:** Enforces that at least one verified copy in every duplicate group is permanently preserved, preventing accidental 100% deletion.
- **Pre-Recycle Revalidation:** Compares file sizes and modification timestamps immediately before recycling to catch files modified post-scan.
- **Recycle Bin Protection:** Uses native Windows Shell APIs (`SHFileOperationW`) to move selected duplicates into the Windows Recycle Bin.

### 7. ⛁ Storage Analyzer
- **Large File Discovery:** Identifies the top 50 largest files across any user-selected drive or directory, categorized by file type (Videos, Archives, Installers, Documents).
- **Cleanable Scratch Caches:** Detects safe temporary caches:
  - User Temporary Files (`%TEMP%`)
  - Application Crash Dumps (`%LOCALAPPDATA%\CrashDumps`)
  - Web browser disk caches (Edge and Chrome)
- **Protected Paths Validation:** Canonical path validation prevents cleanup targeting Windows roots (`C:\Windows`, `System32`), Program Files, or personal user libraries (`Documents`, `Desktop`, `Pictures`).

### 8. 📋 Health Reports
- **Comprehensive Audit:** Summarizes overall system health score (0–100), baseline metrics, detected issues, and verified healthy subsystems.
- **Optimization Impact Tracking:** Captures before/after RAM and disk savings from recent boost actions.
- **Local Export:** Export reports to structured **Markdown (`.md`)** or **JSON (`.json`)** with one click.

### 9. ⚙ Settings & Logs
- **Appearance:** Toggle between Dark Mode, Light Mode, and System Theme.
- **Polling Rate:** Choose telemetry refresh intervals (1.0s, 1.5s, 2.0s, 3.0s).
- **Privacy Assurance:** Complete offline execution guarantee.
- **Activity Logs:** In-app inspection of recent actions with automatic username/path redaction.

---

## 🔒 Safety & Privacy Principles

1. **100% Offline & Private:** Zero network requests, zero telemetry, and zero remote data uploads.
2. **No Unrecoverable Deletions:** Destructive operations default to the Windows Recycle Bin. The permanent deletion fallback (`os.remove`) has been completely removed.
3. **Protected Windows & User Whitelists:** Core OS files, system processes, and personal user folders (`Documents`, `Desktop`, `Pictures`, `Videos`, `Music`) are strictly protected from cleanup.
4. **No Elevation Required for Monitoring:** Operates in standard user mode without requiring Administrator privileges for normal monitoring.

---

## 🚀 Installation & Setup

### Prerequisites
- **Operating System:** Windows 10 (1809+) or Windows 11 (64-bit AMD64/ARM64)
- **Python:** Python 3.10, 3.11, or 3.12 ([Download from python.org](https://www.python.org/))

### Quick Start
1. Clone or download the repository:
   ```bash
   git clone https://github.com/your-username/systemcare.git
   cd systemcare
   ```
2. Run the application using the automated launcher:
   ```cmd
   run.bat
   ```
   *`run.bat` automatically verifies Python in PATH, installs dependencies if missing, and launches the application.*

3. Or install dependencies and run manually:
   ```cmd
   pip install -r requirements.txt
   python main.py
   ```

---

## 🧪 Automated Testing

SystemCare includes an automated test suite containing 40 unit and integration tests covering path canonicalization, process whitelisting, duplicate preservation, Recycle Bin error handling, and headless UI navigation across all 9 screens.

Run all tests:
```cmd
python -m unittest discover -s tests -p "test_*.py" -v
```

CI testing is configured via GitHub Actions (`.github/workflows/tests.yml`) across Python 3.10, 3.11, and 3.12 on `windows-latest`.

---

## 🖼 Screenshots

<!-- Screenshots placeholder -->
| Overview Dashboard | System Health Diagnosis |
| :---: | :---: |
| *(Screenshot Placeholder: Overview)* | *(Screenshot Placeholder: Health)* |

| Safe Boost Mode | Duplicate File Finder |
| :---: | :---: |
| *(Screenshot Placeholder: Boost)* | *(Screenshot Placeholder: Duplicates)* |

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
