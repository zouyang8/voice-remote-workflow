#!/usr/bin/env python3
"""Apply the Xiaomi Remote 2 Pro + SayAll voice workflow."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
import time
import uuid
from pathlib import Path


PLIST_PATH = Path.home() / "Library/Preferences/com.hd838a.RemoteMic.plist"
MACRO_ROOT = Path.home() / "Library/Application Support/Remote Mic/Macros"
MACRO_LIBRARY_PATH = MACRO_ROOT / "library/library.json"
MACRO_BINDINGS_PATH = MACRO_ROOT / "button-bindings.json"
MACRO_SHORTCUTS_PATH = MACRO_ROOT / "private/local-automation-profiles.json"

CMD_FLAG = 131072
MACRO_ID = "local.voice-remote-clear-content"
SELECT_ALL_ID = "shortcut.voice-remote-select-all"
DELETE_ID = "shortcut.voice-remote-delete"


def read_plist() -> dict:
    return plistlib.loads(PLIST_PATH.read_bytes())


def write_plist(data: dict) -> None:
    PLIST_PATH.write_bytes(plistlib.dumps(data))


def read_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def make_profiles(hermes_path: str, codex_path: str, hermes_id: str, codex_id: str) -> list[dict]:
    # Only activate the target app. Sending Cmd+F/Cmd+L during activation can
    # leak the F/L character into a composer when the app is still launching.
    return [
        {
            "id": hermes_id,
            "displayName": "Hermes",
            "bundleIdentifier": "com.nousresearch.hermes",
            "applicationPath": hermes_path,
            "focusStrategy": "none",
            "focusShortcut": {"keyCode": 38, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+L"},
            "accessibilityTarget": None,
        },
        {
            "id": codex_id,
            "displayName": "Codex",
            "bundleIdentifier": "com.openai.codex",
            "applicationPath": codex_path,
            "focusStrategy": "none",
            "focusShortcut": {"keyCode": 33, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+F"},
            "accessibilityTarget": None,
        },
    ]


def make_button_bindings() -> dict:
    return {
        "left": "openCustomApplication",
        "right": "openCustomApplication",
        "ok": "commandReturn",
        "back": "customShortcut",
        "tv": "customShortcut",
        "power": "escape",
        "home": "showDesktop",
        "up": "arrowUp",
        "down": "arrowDown",
        "volume_up": "volumeUp",
        "volume_down": "volumeDown",
        "menu": "contextMenu",
    }


def make_button_shortcuts() -> dict:
    return {
        "back": {"keyCode": 52, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+M"},
        "tv": {"keyCode": 49, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+Space"},
    }


def make_secondary_bindings() -> dict:
    # Safe fallback for SayAll builds that do not load the macro module.
    return {
        "ok": {
            "doubleClick": {"action": "commandDelete"},
            "longPress": {
                "action": "customShortcut",
                "shortcut": {"keyCode": 45, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+N"},
            },
        }
    }


def apply_macro_config(device_id: str) -> None:
    """Persist the two-step OK double-click macro used by current SayAll."""
    library = read_json(MACRO_LIBRARY_PATH, {"definitions": [], "formatVersion": 1})
    definitions = [d for d in library.get("definitions", []) if d.get("macroID") != MACRO_ID and d.get("name") != "全选删除内容"]
    definitions.append(
        {
            "macroID": MACRO_ID,
            "name": "全选删除内容",
            "schemaVersion": "0.3-draft",
            "scope": {"kind": "global"},
            "steps": [
                {"action": "sendKeyboardShortcut", "parameters": {"shortcutProfileKey": SELECT_ALL_ID}, "stepID": "step-select-all"},
                {"action": "sendKeyboardShortcut", "parameters": {"shortcutProfileKey": DELETE_ID}, "stepID": "step-delete"},
            ],
            "summary": "无线麦本机组合动作",
            "version": "1.0.0",
        }
    )
    write_json(MACRO_LIBRARY_PATH, {"definitions": definitions, "formatVersion": 1})

    shortcuts = read_json(MACRO_SHORTCUTS_PATH, {"focusProfiles": [], "formatVersion": 1, "keyboardShortcuts": []})
    kept = [
        s for s in shortcuts.get("keyboardShortcuts", [])
        if s.get("id") not in {SELECT_ALL_ID, DELETE_ID}
        and not str(s.get("displayName", "")).startswith("全选删除内容")
    ]
    kept.extend(
        [
            {"createdAt": "2026-08-21T00:00:00Z", "displayName": "全选删除内容 - 1", "id": SELECT_ALL_ID, "keyCode": 0, "keyLabel": "A", "modifiers": ["command"], "updatedAt": "2026-08-21T00:00:00Z"},
            {"createdAt": "2026-08-21T00:00:00Z", "displayName": "全选删除内容 - 2", "id": DELETE_ID, "keyCode": 51, "keyLabel": "⌫", "modifiers": [], "updatedAt": "2026-08-21T00:00:00Z"},
        ]
    )
    shortcuts["keyboardShortcuts"] = kept
    write_json(MACRO_SHORTCUTS_PATH, shortcuts)

    bindings = read_json(MACRO_BINDINGS_PATH, {"bindings": [], "formatVersion": 1})
    kept_bindings = [
        b for b in bindings.get("bindings", [])
        if not (b.get("button") == "ok" and b.get("remoteProfileID") == device_id and b.get("trigger") == "doubleClick")
        and b.get("macroID") != MACRO_ID
    ]
    kept_bindings.extend(
        [
            {"button": "ok", "remoteProfileID": device_id, "trigger": "doubleClick"},
            {"macroID": MACRO_ID, "version": "1.0.0"},
        ]
    )
    write_json(MACRO_BINDINGS_PATH, {"bindings": kept_bindings, "formatVersion": 1})


def apply_config(hermes_path: str, codex_path: str, device_id: str) -> None:
    data = read_plist()
    hermes_id, codex_id = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    data["customApplicationProfiles"] = json.dumps(make_profiles(hermes_path, codex_path, hermes_id, codex_id), ensure_ascii=False)
    data["buttonBindings"] = json.dumps(make_button_bindings())
    data["buttonApplicationProfileIDs"] = json.dumps({"left": codex_id, "right": hermes_id})
    data["buttonShortcuts"] = json.dumps(make_button_shortcuts())
    try:
        profiles = json.loads(data.get("remoteDeviceProfiles", b"[]"))
    except (TypeError, json.JSONDecodeError):
        profiles = []
    mappings = {
        "buttonBindings": make_button_bindings(),
        "buttonApplicationProfileIDs": {"left": codex_id, "right": hermes_id},
        "buttonShortcuts": make_button_shortcuts(),
        "secondaryButtonBindings": make_secondary_bindings(),
    }
    for profile in profiles:
        if profile.get("deviceIdentifier", "").startswith(device_id):
            profile["mappings"] = mappings
            break
    else:
        profiles.append({"deviceIdentifier": device_id, "mappings": mappings})
    data["remoteDeviceProfiles"] = json.dumps(profiles, ensure_ascii=False)
    data["selectedAudioDeviceUID"] = "MiRemoteV2ch_UID"
    data["gainDB"] = 12
    data["voiceFnTapModeEnabled"] = False
    data["localTranscriptHistoryEnabled"] = True
    write_plist(data)
    apply_macro_config(device_id)


def verify(device_id: str) -> list[str]:
    errors = []
    data = read_plist()
    try:
        profiles = json.loads(data.get("remoteDeviceProfiles", b"[]"))
        profile = next(p for p in profiles if p.get("deviceIdentifier", "").startswith(device_id))
        mappings = profile["mappings"]
        if mappings["buttonBindings"].get("left") != "openCustomApplication": errors.append("left mapping 错误")
        if mappings["buttonBindings"].get("right") != "openCustomApplication": errors.append("right mapping 错误")
    except (StopIteration, KeyError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"设备 profile 解析失败: {exc}")
    try:
        macro = next(d for d in read_json(MACRO_LIBRARY_PATH, {}).get("definitions", []) if d.get("name") == "全选删除内容")
        if [s.get("parameters", {}).get("shortcutProfileKey") for s in macro.get("steps", [])] != [SELECT_ALL_ID, DELETE_ID]:
            errors.append("全选删除组合动作步骤错误")
    except StopIteration:
        errors.append("全选删除组合动作不存在")
    if data.get("gainDB") != 12:
        errors.append(f"gainDB={data.get('gainDB')}")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="DD4402B6")
    parser.add_argument("--hermes-path", default="/Volumes/love/Mac-Offload/Applications/Hermes.app")
    parser.add_argument("--codex-path", default="/Applications/ChatGPT.app")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    data = read_plist()
    try:
        for profile in json.loads(data.get("remoteDeviceProfiles", b"[]")):
            if profile.get("deviceIdentifier", "").startswith(args.device):
                args.device = profile["deviceIdentifier"]
                break
    except (TypeError, json.JSONDecodeError):
        pass

    if not args.verify_only:
        apply_config(args.hermes_path, args.codex_path, args.device)
        print("✅ 配置和 OK 双击全选删除组合动作已写入")
        if not args.no_restart:
            subprocess.run(["killall", "RemoteMic"], capture_output=True)
            time.sleep(2)
            subprocess.run(["open", "/Applications/SayAll.app"], capture_output=True)
            time.sleep(3)
    errors = verify(args.device)
    if errors:
        print("❌ " + "\n  ".join(errors))
        sys.exit(1)
    print("✅ 验证通过")
