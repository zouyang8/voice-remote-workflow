#!/usr/bin/env python3
"""
Apply SayAll remote button configuration for Hermes + Codex workflow.
Usage: python3 apply-config.py [--device DD4402B6...] [--hermes-path /path] [--codex-path /path]
"""
import plistlib, json, uuid, subprocess, sys, argparse, time

PLIST_PATH = f"{__import__('os').path.expanduser('~')}/Library/Preferences/com.hd838a.RemoteMic.plist"

KEYCODES = {"M": 52, "Space": 49, "F": 33, "N": 45, "Return": 36, "Escape": 53, "Tab": 48}
CMD_FLAG = 131072

def make_profiles(hermes_path, codex_path, hermes_id, codex_id):
    return [
        {"id": hermes_id, "displayName": "Hermes", "bundleIdentifier": "com.nousresearch.hermes",
         "applicationPath": hermes_path, "focusStrategy": "keyboardShortcut",
         "focusShortcut": {"keyCode": 33, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+F"},
         "accessibilityTarget": None},
        {"id": codex_id, "displayName": "Codex", "bundleIdentifier": "com.openai.codex",
         "applicationPath": codex_path, "focusStrategy": "keyboardShortcut",
         "focusShortcut": {"keyCode": 33, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+F"},
         "accessibilityTarget": None},
    ]

def make_button_bindings():
    return {"left": "openCustomApplication", "right": "openCustomApplication",
            "ok": "commandReturn", "back": "customShortcut", "tv": "customShortcut",
            "power": "escape", "home": "showDesktop", "up": "arrowUp", "down": "arrowDown",
            "volume_up": "volumeUp", "volume_down": "volumeDown", "menu": "contextMenu"}

def make_button_shortcuts():
    return {"back": {"keyCode": 52, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+M"},
            "tv": {"keyCode": 49, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+Space"}}

def make_secondary_bindings():
    return {"ok": {"longPress": {"action": "customShortcut",
            "shortcut": {"keyCode": 45, "modifierFlagsRawValue": CMD_FLAG, "keyLabel": "Cmd+N"}}}}

def read_plist(): return plistlib.loads(open(PLIST_PATH, "rb").read())
def write_plist(d): plistlib.dump(d, open(PLIST_PATH, "wb"))

def apply_config(hermes_path, codex_path, device_id):
    hermes_id, codex_id = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    d = read_plist()
    d["customApplicationProfiles"] = json.dumps(make_profiles(hermes_path, codex_path, hermes_id, codex_id))
    d["buttonBindings"] = json.dumps(make_button_bindings())
    d["buttonApplicationProfileIDs"] = json.dumps({"left": codex_id, "right": hermes_id})
    d["buttonShortcuts"] = json.dumps(make_button_shortcuts())
    # 设备 profile（真正的配置源）
    try: rdp = json.loads(d.get("remoteDeviceProfiles", b"[]"))
    except: rdp = []
    found = False
    for p in rdp:
        if p.get("deviceIdentifier", "").startswith(device_id):
            p["mappings"] = {"buttonBindings": make_button_bindings(),
                "buttonApplicationProfileIDs": {"left": codex_id, "right": hermes_id},
                "buttonShortcuts": make_button_shortcuts(),
                "secondaryButtonBindings": make_secondary_bindings()}
            found = True; break
    if not found:
        rdp.append({"deviceIdentifier": device_id, "mappings": {
            "buttonBindings": make_button_bindings(),
            "buttonApplicationProfileIDs": {"left": codex_id, "right": hermes_id},
            "buttonShortcuts": make_button_shortcuts(),
            "secondaryButtonBindings": make_secondary_bindings()}})
    d["remoteDeviceProfiles"] = json.dumps(rdp)
    d["selectedAudioDeviceUID"] = "MiRemoteV2ch_UID"
    d["voiceFnTapModeEnabled"] = False
    d["localTranscriptHistoryEnabled"] = True
    write_plist(d)
    return hermes_id, codex_id

def verify():
    d = read_plist(); errors = []
    try:
        rdp = json.loads(d.get("remoteDeviceProfiles", b"[]"))
        if not rdp: errors.append("remoteDeviceProfiles 为空")
        for p in rdp:
            bb = p.get("mappings", {}).get("buttonBindings", {})
            if bb.get("left") != "openCustomApplication": errors.append(f"left={bb.get('left')}")
            if bb.get("right") != "openCustomApplication": errors.append(f"right={bb.get('right')}")
    except Exception as e: errors.append(f"解析失败: {e}")
    return errors

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="DD4402B6")
    ap.add_argument("--hermes-path", default="/Volumes/love/Mac-Offload/Applications/Hermes.app")
    ap.add_argument("--codex-path", default="/Applications/ChatGPT.app")
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    if a.verify_only:
        errs = verify()
        print("✅ 通过" if not errs else "❌ " + "\n  ".join(errs)); sys.exit(0 if not errs else 1)
    # 查找完整设备 ID
    d = read_plist()
    try:
        for p in json.loads(d.get("remoteDeviceProfiles", b"[]")):
            if p.get("deviceIdentifier", "").startswith(a.device): a.device = p["deviceIdentifier"]; break
    except: pass
    print(f"设备: {a.device}"); print(f"Hermes: {a.hermes_path}"); print(f"Codex: {a.codex_path}")
    hid, cid = apply_config(a.hermes_path, a.codex_path, a.device)
    print(f"✅ 配置已写入")
    subprocess.run(["killall", "RemoteMic"], capture_output=True); time.sleep(2)
    subprocess.run(["open", "/Applications/SayAll.app"], capture_output=True); time.sleep(3)
    print("✅ SayAll 已重启" if subprocess.run(["pgrep", "-x", "RemoteMic"], capture_output=True).returncode == 0 else "❌ 启动失败")
    errs = verify()
    if errs: print("⚠️ " + "\n  ".join(errs))
    else: print("✅ 验证通过")
