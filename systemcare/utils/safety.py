"""
Safety guardrails and system protection mechanisms for SystemCare.
Ensures critical OS processes, system directories, and personal files
are strictly guarded against accidental termination or deletion.
"""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Set

# Essential Windows processes that must NEVER be terminated
PROTECTED_PROCESS_NAMES: Set[str] = {
    # System core
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "fontdrvhost.exe",
    "dwm.exe",
    "explorer.exe",
    "sihost.exe",
    "taskhostw.exe",
    "svchost.exe",
    "spoolsv.exe",
    "audiodg.exe",
    "ctfmon.exe",
    "runtimebroker.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "searchindexer.exe",
    "searchhost.exe",
    # Windows Security / Defender
    "msmpeng.exe",
    "nissrv.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    "smartscreen.exe",
    # Hardware & drivers
    "nvcontainer.exe",
    "igfxcuiservice.exe",
    "igfxtray.exe",
    "amdfendrsr.exe",
    "rtkngui64.exe",
    # Self protection
    "python.exe",
    "pythonw.exe",
}

# Critical OS swap/hibernation files
CRITICAL_SYSTEM_FILES: Set[str] = {
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "dumpstack.log.tmp",
    "bootmgr",
    "bootnxt",
    "ntuser.dat",
    "usrclass.dat",
}


def canonicalize_path(p: str) -> str:
    """
    Produce a canonical, normalized, case-folded path for Windows.
    Resolves symlinks, directory junctions, and relative segments ('..').
    Strips Windows extended path prefix ('\\\\?\\') if present.
    """
    if not p:
        return ""
    try:
        raw = str(p).strip()
        if raw.startswith("\\\\?\\"):
            raw = raw[4:]
        # Use realpath to resolve symlinks and reparse points
        real = os.path.realpath(os.path.abspath(raw))
        norm = os.path.normpath(real)
        return os.path.normcase(norm)
    except Exception:
        # Fallback to simple normpath if realpath fails
        try:
            return os.path.normcase(os.path.normpath(os.path.abspath(str(p))))
        except Exception:
            return ""


def _get_protected_user_roots() -> Set[str]:
    """Retrieve normalized personal user folder roots that must be guarded."""
    user_prof = os.environ.get("USERPROFILE", "")
    roots: Set[str] = set()
    if user_prof:
        c_prof = canonicalize_path(user_prof)
        if c_prof:
            roots.add(c_prof)
            # Personal libraries
            for sub in [
                "Documents",
                "Desktop",
                "Pictures",
                "Music",
                "Videos",
                "Downloads",
                "Saved Games",
                "Favorites",
                "OneDrive",
            ]:
                sub_path = canonicalize_path(os.path.join(user_prof, sub))
                if sub_path:
                    roots.add(sub_path)

    # OneDrive user root if configured
    onedrive = os.environ.get("OneDrive", "")
    if onedrive:
        c_od = canonicalize_path(onedrive)
        if c_od:
            roots.add(c_od)

    return roots


def _get_protected_system_roots() -> Set[str]:
    """Retrieve normalized Windows operating system directories that must be guarded."""
    roots: Set[str] = set()
    for env_var in ["SystemRoot", "windir"]:
        val = os.environ.get(env_var, r"C:\Windows")
        c = canonicalize_path(val)
        if c:
            roots.add(c)
            roots.add(canonicalize_path(os.path.join(val, "System32")))
            roots.add(canonicalize_path(os.path.join(val, "SysWOW64")))
            roots.add(canonicalize_path(os.path.join(val, "WinSxS")))

    for env_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData"]:
        val = os.environ.get(env_var, "")
        if val:
            c = canonicalize_path(val)
            if c:
                roots.add(c)

    return roots


def _get_allowlisted_cleanable_roots() -> Set[str]:
    """
    Retrieve explicitly allowlisted root directories where automatic/scratch cleaning is permitted.
    Files outside these directories cannot be targeted by automated cleaners.
    """
    allowed: Set[str] = set()

    # 1. User Temp directories
    for env_var in ["TEMP", "TMP"]:
        val = os.environ.get(env_var, "")
        if val:
            c = canonicalize_path(val)
            if c:
                allowed.add(c)

    # 2. LocalAppData CrashDumps and Browser caches
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        crash_dumps = canonicalize_path(os.path.join(local_app, "CrashDumps"))
        if crash_dumps:
            allowed.add(crash_dumps)
        edge_cache = canonicalize_path(
            os.path.join(local_app, "Microsoft", "Edge", "User Data", "Default", "Cache", "Cache_Data")
        )
        if edge_cache:
            allowed.add(edge_cache)
        chrome_cache = canonicalize_path(
            os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Cache", "Cache_Data")
        )
        if chrome_cache:
            allowed.add(chrome_cache)

    return allowed


def is_system_process(pid: int, name: str) -> bool:
    """
    Check if a process is a critical system service or OS component.
    Always returns True for kernel PIDs (0, 4) and whitelisted OS services.
    """
    if pid in (0, 4):
        return True
    if not name:
        return True
    clean_name = name.lower().strip()
    return clean_name in PROTECTED_PROCESS_NAMES


def is_protected_cleanup_path(file_or_dir_path: str) -> bool:
    """
    Verify whether a path is protected from cleanup or deletion.
    Returns True (protected) if the path points to, resides inside, or links into:
      - Drive roots (e.g. C:\\)
      - Windows OS folders (C:\\Windows, System32, WinSxS)
      - Program Files / ProgramData
      - User Profile root (C:\\Users\\username)
      - Personal User folders (Documents, Desktop, Pictures, Videos, Music, etc.) and ALL subdirectories/files within them
      - Critical OS files (pagefile.sys, hiberfil.sys, etc.)
    Fails safely (returns True) on any parsing or validation error.
    """
    if not file_or_dir_path:
        return True

    try:
        target_canon = canonicalize_path(file_or_dir_path)
    except Exception:
        return True

    if not target_canon:
        return True

    # 1. Check drive root (e.g. 'c:\\' or 'c:')
    drive, rest = os.path.splitdrive(target_canon)
    if rest in ("", "\\", "/"):
        return True

    # 2. Check against critical system files by base name
    file_name = os.path.basename(target_canon)
    if file_name in CRITICAL_SYSTEM_FILES:
        return True

    # 3. Check personal user directories and ALL subdirectories/files inside them
    user_roots = _get_protected_user_roots()
    for u_root in user_roots:
        if not u_root:
            continue
        # Direct match with the user directory root
        if target_canon == u_root:
            return True
        # Match any child file or subdirectory inside the user directory root
        if target_canon.startswith(u_root + "\\") or target_canon.startswith(u_root + "/"):
            # Ensure safe scratch folders inside %USERPROFILE%\AppData\Local\Temp are NOT blocked
            # by the user profile root check, but personal documents/desktop ARE strictly blocked.
            user_temp = canonicalize_path(os.environ.get("TEMP", ""))
            if user_temp and (target_canon == user_temp or target_canon.startswith(user_temp + "\\") or target_canon.startswith(user_temp + "/")):
                continue
            local_app = canonicalize_path(os.environ.get("LOCALAPPDATA", ""))
            # Allow CrashDumps and browser caches inside LocalAppData
            if local_app:
                crash_dumps = canonicalize_path(os.path.join(local_app, "CrashDumps"))
                if crash_dumps and (target_canon == crash_dumps or target_canon.startswith(crash_dumps + "\\")):
                    continue
                cache_dirs = [
                    canonicalize_path(os.path.join(local_app, "Microsoft", "Edge", "User Data", "Default", "Cache", "Cache_Data")),
                    canonicalize_path(os.path.join(local_app, "Google", "Chrome", "User Data", "Default", "Cache", "Cache_Data")),
                ]
                if any(cd and (target_canon == cd or target_canon.startswith(cd + "\\")) for cd in cache_dirs):
                    continue

            return True

    # 4. Check system directories and ALL subdirectories/files inside them
    sys_roots = _get_protected_system_roots()
    win_temp = canonicalize_path(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"))
    for s_root in sys_roots:
        if not s_root:
            continue
        if target_canon == s_root:
            return True
        if target_canon.startswith(s_root + "\\") or target_canon.startswith(s_root + "/"):
            # Disallow deleting inside Windows even if inside Windows\Temp for safety
            return True

    # 5. Check if original input path was a symlink/junction pointing elsewhere
    try:
        raw_norm = os.path.normcase(os.path.normpath(os.path.abspath(file_or_dir_path)))
        if os.path.islink(raw_norm) or hasattr(os, "readlink"):
            try:
                link_target = os.path.realpath(raw_norm)
                c_link = canonicalize_path(link_target)
                if c_link != target_canon:
                    # Verify the resolved target recursively
                    if is_protected_cleanup_path(c_link):
                        return True
            except Exception:
                pass
    except Exception:
        pass

    return False


def is_allowlisted_cleanup_path(file_path: str) -> bool:
    """
    Verify whether a path strictly resides inside an allowlisted temporary cleanup root.
    Used to guarantee automatic cleaners never wander outside permitted scratch areas.
    """
    if not file_path or is_protected_cleanup_path(file_path):
        return False

    canon = canonicalize_path(file_path)
    if not canon:
        return False

    allowed_roots = _get_allowlisted_cleanable_roots()
    for a_root in allowed_roots:
        if not a_root:
            continue
        if canon == a_root:
            # Don't wipe the root directory itself, only files inside it
            return False
        if canon.startswith(a_root + "\\") or canon.startswith(a_root + "/"):
            return True

    return False


# Native Windows Shell File Operation for Recycle Bin
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


FO_DELETE = 0x0003
FOF_ALLOWUNDO = 0x0040        # Moves to Recycle Bin
FOF_NOCONFIRMATION = 0x0010   # Don't show Windows generic prompt
FOF_SILENT = 0x0004           # Don't show Windows progress animation
FOF_NOERRORUI = 0x0400        # Don't display shell error box

# Configure ctypes signatures for SHFileOperationW
_shell32 = ctypes.windll.shell32
_SHFileOperationW = _shell32.SHFileOperationW
_SHFileOperationW.argtypes = [ctypes.POINTER(SHFILEOPSTRUCTW)]
_SHFileOperationW.restype = ctypes.c_int


def send_to_recycle_bin(file_path: str) -> bool:
    """
    Safely move a file or folder to the Windows Recycle Bin using SHFileOperationW.
    Revalidates path against safety boundaries immediately prior to invocation.
    Never falls back to irreversible permanent deletion.
    """
    if not file_path or not os.path.exists(file_path):
        return False

    # Immediate pre-operation safety revalidation
    if is_protected_cleanup_path(file_path):
        raise PermissionError(f"Safety guard: path '{file_path}' is protected from deletion.")

    # SHFileOperationW requires a double-null-terminated string
    abs_path = os.path.abspath(file_path)
    path_double_null = abs_path + "\x00\x00"

    fileop = SHFILEOPSTRUCTW()
    fileop.hwnd = None
    fileop.wFunc = FO_DELETE
    fileop.pFrom = path_double_null
    fileop.pTo = None
    fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

    try:
        result = _SHFileOperationW(ctypes.byref(fileop))
        # Operation succeeded if result == 0, not aborted, and target no longer exists at source
        success = (result == 0) and (not fileop.fAnyOperationsAborted) and (not os.path.exists(file_path))
        return success
    except Exception:
        return False
