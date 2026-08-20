---
name: sayall-remote-config
description: "Configure SayAll + Xiaomi BT Remote for Hermes/Codex voice input workflow."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macos, sayall, remote, voice-input, bluetooth, automation]
---

# SayAll 遥控器配置（Hermes + Codex 语音输入）

用小米蓝牙遥控器 2 Pro + SayAll v1.9.4+ 实现：
- 一键切换 Hermes / Codex 并自动聚焦输入框
- 语音键按住说话，松开转录
- ok 键发送，长按 ok 新建对话
- 返回键最小化窗口，TV 键切换输入法

## 前置条件

- macOS 12+
- SayAll v1.9.3+ 已安装（`/Applications/SayAll.app`）
- 小米蓝牙遥控器 2 Pro 已配对
- MiRemoteV 2ch 虚拟麦驱动已安装（`/Library/Audio/Plug-Ins/HAL/MiRemoteV2ch.driver`）
- 豆包输入法已安装（语音转录用）
- Hermes Desktop 已安装
- ChatGPT/Codex 桌面版已安装

## 快速恢复（一键配置）

```bash
python3 ~/.hermes/skills/devops/sayall-remote-config/scripts/apply-config.py
```

支持参数：

```bash
python3 scripts/apply-config.py \
  --hermes-path /Volumes/love/Mac-Offload/Applications/Hermes.app \
  --codex-path /Applications/ChatGPT.app \
  --device DD4402B6...
```

仅验证不写入：

```bash
python3 scripts/apply-config.py --verify-only
```

## 完整按键映射

| 遥控器按键 | 动作 | 效果 |
|-----------|------|------|
| 左键 | `openCustomApplication` | 打开/聚焦 Codex + Cmd+F 聚焦输入框 |
| 右键 | `openCustomApplication` | 打开/聚焦 Hermes + Cmd+F 聚焦输入框 |
| ok 键（单击）| `commandReturn` | Cmd+Return 发送消息 |
| ok 键（长按）| `Cmd+N` | 新建对话（Hermes/Codex 通用） |
| 返回键 | `Cmd+M` | 最小化当前窗口 |
| TV 键 | `Cmd+Space` | 切换输入法（→豆包） |
| 语音键 | 录音 | 按住说话，松开豆包转录 |
| 电源键 | escape | 取消/退出 |
| 主页键 | showDesktop | 显示桌面 |

## 使用流程

```
1. 按左键/右键 → 切到 Codex/Hermes（自动聚焦输入框）
2. 按 TV 键 → 切到豆包输入法
3. 按住语音键说话 → 松开，文字出现在输入框
4. 按 ok 键 → 发送消息
5. 按返回键 → 最小化当前窗口
6. 长按 ok 键 → 新建对话
```

## 配置原理（排错必读）

### Plist 配置结构

配置文件：`~/Library/Preferences/com.hd838a.RemoteMic.plist`

**关键：SayAll 启动时，设备 profile 的 mappings 会覆盖顶层配置。**

```
plist
├── buttonBindings               ← 顶层（备用，会被覆盖）
├── buttonApplicationProfileIDs  ← 顶层（备用）
├── buttonShortcuts              ← 顶层（备用）
├── customApplicationProfiles    ← App 注册列表（Hermes/Codex 的路径+聚焦策略）
├── remoteDeviceProfiles         ← ★ 真正的配置源（按设备存储）
│   └── [{
│       deviceIdentifier: "DD4402B6…",
│       mappings: {
│         buttonBindings: {...},
│         buttonApplicationProfileIDs: {left: codex_id, right: hermes_id},
│         buttonShortcuts: {back: Cmd+M, tv: Cmd+Space},
│         secondaryButtonBindings: {ok: {longPress: Cmd+N}}
│       }
│     }]
├── selectedAudioDeviceUID       ← "MiRemoteV2ch_UID"
├── voiceFnTapModeEnabled        ← false（关掉点触模式，适配豆包）
└── localTranscriptHistoryEnabled ← true
```

### customShortcut 格式

```json
{
  "keyCode": 52,           // macOS virtual key code
  "modifierFlagsRawValue": 131072,  // kCGEventFlagMaskCommand
  "keyLabel": "Cmd+M"
}
```

常用 keyCode：M=52, Space=49, F=33, N=45, Tab=48, Escape=53

### openCustomApplication 流程

1. 按 left/right → SayAll 查 `buttonApplicationProfileIDs[left/right]` 得到 profile ID
2. 用 profile ID 在 `customApplicationProfiles` 中查找对应 App
3. 打开 App（`applicationPath`）
4. 按 `focusStrategy` 聚焦输入框：
   - `keyboardShortcut` → 发送 `focusShortcut`（如 Cmd+F）
   - `recordedAccessibility` → 需要用户在 SayAll GUI 中手动录制

### 为什么不用预置 openCodex？

`openCodex` 是 SayAll 内置动作，直接打开 ChatGPT.app，但它的聚焦策略用 accessibility 找 composer 输入框，在当前版本会报 `composer_not_found`。改用 `openCustomApplication` + `focusStrategy: keyboardShortcut` 可靠得多。

## 常见问题排错

### 按键没反应 / 配置不生效

```bash
# 1. 检查配置是否写到了设备 profile（而不是只写了顶层）
python3 -c "
import plistlib, json
d = plistlib.loads(open('$HOME/Library/Preferences/com.hd838a.RemoteMic.plist','rb').read())
rdp = json.loads(d.get('remoteDeviceProfiles', b'[]'))
for p in rdp:
    m = p.get('mappings', {})
    print('left:', m.get('buttonBindings', {}).get('left'))
    print('right:', m.get('buttonBindings', {}).get('right'))
"
```

期望输出 `left: openCustomApplication` 和 `right: openCustomApplication`。如果输出是 `openCodex`，说明配置写到了顶层但没写设备 profile。

### 切换后语音无法输入

- **症状**：切换到 App 后按语音键，文字没进输入框
- **日志**：`TRANSCRIPT CAPTURE skipped reason=initial_focus_unavailable`
- **原因**：`focusStrategy: none` 或 `accessibilityTarget` 未录制
- **解决**：确保 `customApplicationProfiles` 中对应 App 的 `focusStrategy` 为 `keyboardShortcut`，且 `focusShortcut` 已设置

### 右键无法切到 Hermes

- **症状**：左键可以切到 Codex，右键切不到 Hermes
- **日志**：`APP ACTION custom unavailable reason=profile_missing`
- **原因**：`buttonApplicationProfileIDs[right]` 缺失或 ID 不匹配
- **解决**：确保 `buttonApplicationProfileIDs` 中 right 对应的 UUID 与 `customApplicationProfiles` 中 Hermes 的 id 完全一致（大小写敏感）

### Cmd+F 无法聚焦输入框

- **Hermes**：Cmd+F 打开搜索栏，搜索栏就是可输入的，文字能进去 ✅
- **Codex**：同上 ✅
- 如果换了其他 App，需要测试该 App 的 Cmd+F 行为，或改用其他快捷键

### 语音转录没反应

```bash
# 检查音频设备
log stream --predicate 'process == "RemoteMic"' --style compact | grep -i audio
```

- 确认 MiRemoteV 2ch 是系统默认输入设备（系统设置→声音→输入）
- 确认 `selectedAudioDeviceUID` 设为 `MiRemoteV2ch_UID`
- 确认 `voiceFnTapModeEnabled` 为 false

### 日志位置

```bash
tail -50 ~/Library/Logs/RemoteMic/runtime.log
```

关键日志前缀：
- `HID BUTTON` — 按键事件
- `APP ACTION` — App 打开/切换动作
- `APP FOCUS` — 焦点聚焦结果
- `SHORTCUT ACTION` — 快捷键发送
- `TRANSCRIPT CAPTURE` — 语音转录

### 重新配对遥控器后配置丢失

设备 ID 会变，需要更新 `remoteDeviceProfiles` 中的 `deviceIdentifier`。运行：

```bash
python3 scripts/apply-config.py --device <新设备ID前缀>
```

### SayAll 版本升级后配置不兼容

1. 先备份：`cp ~/Library/Preferences/com.hd838a.RemoteMic.plist ~/Desktop/RemoteMic.plist.bak`
2. 升级 SayAll
3. 检查日志是否报 `UNKNOWN ACTION` 或 `UNSUPPORTED`
4. 如有，查看新版源码（解压 SayAll.app）确认动作名变化，更新 apply-config.py

## 从零手动配置（无脚本）

如果脚本不可用，按以下顺序操作：

1. **提取源码**（查看支持的 action 类型）：
   ```bash
   cd ~/.hermes/tmp-sayall-install && dpkg-deb -R /Applications/SayAll.app expanded/
   ```

2. **确认 App 路径和 Bundle ID**：
   ```bash
   mdfind "kMDItemCFBundleIdentifier == 'com.nousresearch.hermes'"
   mdfind "kMDItemCFBundleIdentifier == 'com.openai.codex'"
   ```

3. **用 Python 写入 plist**（参考 scripts/apply-config.py 源码）

4. **重启 SayAll**：`killall RemoteMic && sleep 2 && open /Applications/SayAll.app`

5. **查日志验证**：`tail -50 ~/Library/Logs/RemoteMic/runtime.log`
