"""
Startup Application Manager.
Scans Windows startup locations (Registry HKCU/HKLM and Startup Folders),
evaluates startup impact, provides clear safety guidance, and allows safe,
confirmed toggling of user-level startup items with full backup and rollback handling.
"""

import os
import winreg
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..utils.logger import logger
from ..utils.safety import PROTECTED_PROCESS_NAMES

HKCU_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
HKLM_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
HKCU_DISABLED_KEY = r"Software\SystemCare\DisabledStartup"

# Common applications and their known impacts
KNOWN_STARTUP_CATALOG: Dict[str, Dict[str, str]] = {
    "onedrive": {
        "impact": "Medium",
        "description": "Microsoft OneDrive cloud file synchronization.",
        "guidance": "Safe to disable if you prefer to sync files on-demand or want faster boot times.",
    },
    "securityhealth": {
        "impact": "Essential",
        "description": "Windows Security Center notification icon and protection tray.",
        "guidance": "Essential: Keep enabled to maintain real-time security alerts.",
    },
    "msmpeng": {
        "impact": "Essential",
        "description": "Microsoft Defender Antivirus core service.",
        "guidance": "Essential: Do not disable system security services.",
    },
    "steam": {
        "impact": "High",
        "description": "Steam gaming client auto-start.",
        "guidance": "Safe to disable. Launch Steam when you are ready to play games.",
    },
    "epicgameslauncher": {
        "impact": "High",
        "description": "Epic Games launcher auto-start background tray.",
        "guidance": "Safe to disable. Launch Epic Games manually when playing games.",
    },
    "discord": {
        "impact": "Medium",
        "description": "Discord communication application.",
        "guidance": "Safe to disable. Start Discord manually when needed.",
    },
    "spotify": {
        "impact": "Medium",
        "description": "Spotify music player.",
        "guidance": "Safe to disable to conserve startup memory and CPU.",
    },
    "microsoftedgeautolaunch": {
        "impact": "Low",
        "description": "Microsoft Edge pre-launch background helper.",
        "guidance": "Safe to disable. Edge will start normally when clicked.",
    },
    "googlechromeautolaunch": {
        "impact": "Low",
        "description": "Google Chrome background launch agent.",
        "guidance": "Safe to disable. Chrome will launch normally when clicked.",
    },
    "operastable": {
        "impact": "Medium",
        "description": "Opera browser auto-launcher.",
        "guidance": "Safe to disable. Start Opera manually when browsing.",
    },
    "deskrest": {
        "impact": "Low",
        "description": "DeskRest break reminder utility.",
        "guidance": "Optional utility. Safe to manage based on your workflow.",
    },
}


@dataclass
class StartupItem:
    id: str
    name: str
    command: str
    location_type: str  # "Registry (User)", "Registry (System)", "Startup Folder (User)", "Startup Folder (All Users)"
    location_path: str
    is_enabled: bool
    impact: str  # "Essential", "High", "Medium", "Low", "Unknown"
    description: str
    guidance: str
    can_toggle: bool  # Can be safely toggled in current user session


class StartupManager:
    """
    Manages startup application identification and safe modification.
    Enforces automatic backup and atomic rollback on registry changes.
    """

    def __init__(self) -> None:
        self.user_startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
        self.common_startup_dir = os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup")

    def list_startup_items(self) -> List[StartupItem]:
        """
        Scan all active and disabled startup entries from Registry and Startup directories.
        """
        items: List[StartupItem] = []

        # 1. Registry HKCU Run (Active)
        items.extend(self._scan_registry_key(winreg.HKEY_CURRENT_USER, HKCU_RUN, "Registry (User)", enabled=True))

        # 2. Registry HKCU Disabled (Backed up by SystemCare)
        items.extend(self._scan_registry_key(winreg.HKEY_CURRENT_USER, HKCU_DISABLED_KEY, "Registry (User)", enabled=False))

        # 3. Registry HKLM Run (Active)
        items.extend(self._scan_registry_key(winreg.HKEY_LOCAL_MACHINE, HKLM_RUN, "Registry (System)", enabled=True))

        # 4. User Startup Folder
        items.extend(self._scan_startup_folder(self.user_startup_dir, "Startup Folder (User)"))

        # 5. Common Startup Folder
        items.extend(self._scan_startup_folder(self.common_startup_dir, "Startup Folder (All Users)"))

        return items

    def _scan_registry_key(
        self, root: int, subkey: str, location_label: str, enabled: bool
    ) -> List[StartupItem]:
        items: List[StartupItem] = []
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
                count = winreg.QueryInfoKey(key)[1]
                for i in range(count):
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        impact, desc, guide = self._analyze_startup_entry(name, val)
                        is_sys_root = (root == winreg.HKEY_LOCAL_MACHINE)
                        is_essential = (impact == "Essential")
                        can_toggle = not is_sys_root and not is_essential

                        items.append(
                            StartupItem(
                                id=f"{location_label}_{name}",
                                name=name,
                                command=str(val),
                                location_type=location_label,
                                location_path=subkey,
                                is_enabled=enabled,
                                impact=impact,
                                description=desc,
                                guidance=guide,
                                can_toggle=can_toggle,
                            )
                        )
                    except Exception as err:
                        logger.debug(f"Error reading registry value: {err}")
        except FileNotFoundError:
            pass
        except PermissionError:
            logger.warning(f"Permission denied accessing registry key: {subkey}")
        except Exception as err:
            logger.error(f"Error reading registry key {subkey}: {err}")

        return items

    def _scan_startup_folder(self, folder_path: str, location_label: str) -> List[StartupItem]:
        items: List[StartupItem] = []
        if not os.path.exists(folder_path):
            return items

        try:
            for fname in os.listdir(folder_path):
                fpath = os.path.join(folder_path, fname)
                is_disabled = fname.endswith(".disabled")
                is_lnk = fname.endswith(".lnk") or is_disabled

                if is_lnk:
                    clean_name = fname.replace(".disabled", "").replace(".lnk", "")
                    impact, desc, guide = self._analyze_startup_entry(clean_name, fpath)
                    is_all_users = "All Users" in location_label
                    can_toggle = not is_all_users and impact != "Essential"

                    items.append(
                        StartupItem(
                            id=f"{location_label}_{fname}",
                            name=clean_name,
                            command=fpath,
                            location_type=location_label,
                            location_path=folder_path,
                            is_enabled=not is_disabled,
                            impact=impact,
                            description=desc or "Shortcut in Windows Startup directory.",
                            guidance=guide,
                            can_toggle=can_toggle,
                        )
                    )
        except Exception as err:
            logger.warning(f"Error scanning startup directory '{folder_path}': {err}")

        return items

    def _analyze_startup_entry(self, name: str, command: str) -> Tuple[str, str, str]:
        """Classify impact, description, and guidance for a startup application."""
        clean_name = name.lower().replace(" ", "").replace("_", "")
        clean_cmd = str(command).lower()

        # Check known catalog
        for known_key, meta in KNOWN_STARTUP_CATALOG.items():
            if known_key in clean_name or known_key in clean_cmd:
                return meta["impact"], meta["description"], meta["guidance"]

        # Check against protected Windows components
        for p in PROTECTED_PROCESS_NAMES:
            if p in clean_name or p in clean_cmd:
                return (
                    "Essential",
                    "Windows Operating System service or component.",
                    "Essential: Must remain enabled for normal Windows operation.",
                )

        return (
            "Medium",
            "Third-party application startup entry.",
            "Safe to disable if you do not need this application running automatically upon signing in.",
        )

    def toggle_startup_item(self, item: StartupItem) -> Tuple[bool, str]:
        """
        Safely toggle a startup item between enabled and disabled with user confirmation.
        Enforces safety checks against essential items and ensures atomic rollback.
        Returns (success, message).
        """
        # Revalidate item safety
        impact, _, _ = self._analyze_startup_entry(item.name, item.command)
        if impact == "Essential" or item.impact == "Essential":
            return False, "This is an essential Windows component or security service and cannot be disabled."

        if not item.can_toggle:
            if "System" in item.location_type or "All Users" in item.location_type:
                return (
                    False,
                    "This startup entry is system-wide (HKLM or Common Startup). To modify it safely, please use "
                    "Windows Settings > Apps > Startup.",
                )
            return False, "This startup item cannot be safely modified."

        # Case 1: Registry HKCU
        if "Registry" in item.location_type:
            return self._toggle_registry_item(item)

        # Case 2: Startup Folder (User)
        if "Startup Folder" in item.location_type:
            return self._toggle_folder_item(item)

        return False, "Unknown startup item location."

    def _toggle_registry_item(self, item: StartupItem) -> Tuple[bool, str]:
        """
        Toggle registry startup entry between HKCU Run and HKCU DisabledStartup.
        Implements backup and rollback to prevent entry loss on write failure.
        """
        src_key_name = HKCU_RUN if item.is_enabled else HKCU_DISABLED_KEY
        dst_key_name = HKCU_DISABLED_KEY if item.is_enabled else HKCU_RUN
        action_name = "disabled" if item.is_enabled else "enabled"

        # 1. Read existing value from source
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, src_key_name, 0, winreg.KEY_READ) as src_key:
                val, reg_type = winreg.QueryValueEx(src_key, item.name)
        except FileNotFoundError:
            return False, f"Startup entry '{item.name}' was not found in registry."
        except Exception as err:
            return False, f"Could not access source registry entry '{item.name}': {err}"

        # 2. Write to destination backup/active key
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, dst_key_name) as dst_key:
                winreg.SetValueEx(dst_key, item.name, 0, reg_type, val)
        except Exception as err:
            return False, f"Failed to backup startup entry '{item.name}' to destination key: {err}"

        # 3. Delete from source key (with rollback if delete fails)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, src_key_name, 0, winreg.KEY_SET_VALUE) as src_key:
                winreg.DeleteValue(src_key, item.name)
        except Exception as err:
            # Rollback: remove the value we wrote to dst_key
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, dst_key_name, 0, winreg.KEY_SET_VALUE) as dst_key:
                    winreg.DeleteValue(dst_key, item.name)
            except Exception:
                pass
            msg = f"Failed to delete source entry '{item.name}'; rolled back changes: {err}"
            logger.error(msg)
            return False, msg

        logger.info(f"Startup item '{item.name}' {action_name} successfully in HKCU registry.")
        return True, f"Startup application '{item.name}' has been {action_name}."

    def _toggle_folder_item(self, item: StartupItem) -> Tuple[bool, str]:
        file_path = item.command
        if not os.path.exists(file_path):
            return False, f"Startup shortcut '{file_path}' does not exist on disk."

        try:
            if item.is_enabled:
                new_path = file_path + ".disabled"
                action_name = "disabled"
            else:
                new_path = file_path.replace(".disabled", "")
                action_name = "enabled"

            os.rename(file_path, new_path)
            logger.info(f"Startup shortcut '{item.name}' {action_name} successfully.")
            return True, f"Startup shortcut '{item.name}' has been {action_name}."
        except Exception as err:
            msg = f"Failed to rename startup shortcut '{item.name}': {err}"
            logger.error(msg)
            return False, msg
