# 🎤 小米遥控器语音工作流

> 小米蓝牙遥控器 2 Pro + SayAll + Hermes/Codex，尽量不用鼠标。

这套配置适用于 macOS、SayAll/无线麦、Hermes 和 Codex。它把遥控器的切换、发送、清空、音量和语音输入统一起来。

## 当前配置

| 遥控器按键 | 动作 | 说明 |
|---|---|---|
| 左键 | 打开 Codex | 只激活 App，不再发送 `Cmd+F`，避免漏出 `F` 字母 |
| 右键 | 打开 Hermes | 只激活 App，不再发送 `Cmd+L`，避免漏出 `L` 字母 |
| OK 单击 | `Command+Return` | 发送消息 |
| OK 双击 | 组合动作：`Command+A` → `Delete` | 全选并清空单行或多行输入 |
| OK 长按 | `Command+N` | 新建对话 |
| 返回键 | `Command+M` | 最小化当前窗口 |
| TV 键 | `Command+Space` | 切换输入法 |
| 语音键 | 按住说话 | 松开后交给豆包转录 |
| 电源键 | `Escape` | 取消或退出 |
| 主页键 | 显示桌面 |  |
| 音量 +/- | 系统音量 |  |

当前语音增益为 `12 dB`，音频设备为 `MiRemoteV 2ch`。遥控器语音键保持“按住说话”，Fn 点按模式关闭。

## 前置条件

- macOS 12+
- SayAll/无线麦已安装
- 小米蓝牙遥控器 2 Pro 已配对
- `MiRemoteV 2ch` 驱动已安装
- 豆包输入法、Hermes Desktop、Codex 桌面版已安装
- 已给 SayAll 开启输入监控和辅助功能权限

## 快速恢复

```bash
python3 apply-config.py
```

指定应用路径或只验证：

```bash
python3 apply-config.py \
  --hermes-path /Volumes/love/Mac-Offload/Applications/Hermes.app \
  --codex-path /Applications/ChatGPT.app

python3 apply-config.py --verify-only
```

如需写入配置但暂不重启无线麦：

```bash
python3 apply-config.py --no-restart
```

脚本会同时更新：

- `~/Library/Preferences/com.hd838a.RemoteMic.plist`
- `~/Library/Application Support/Remote Mic/Macros/library/library.json`
- `~/Library/Application Support/Remote Mic/Macros/private/local-automation-profiles.json`
- `~/Library/Application Support/Remote Mic/Macros/button-bindings.json`

其中 OK 双击的“全选删除内容”是一个两步组合动作，不依赖 `Command+Delete`，因此多行内容也会全部清掉。

## 使用流程

1. 按左键或右键切换到 Codex/Hermes。
2. 在目标 App 的输入框中输入或按住语音键说话。
3. 松开语音键，等待豆包完成转录。
4. 单击 OK 发送。
5. 双击 OK 全选并删除当前输入内容。
6. 长按 OK 新建对话。

切换 App 时现在只负责激活窗口，不发送通用聚焦快捷键。这样可以避免应用还没完成激活时，把 `F` 或 `L` 写进输入框；如果目标 App 没有恢复上次输入焦点，需要手动点一下输入框。

## 配置原理

SayAll 的实际遥控器配置保存在 `remoteDeviceProfiles` 的设备 profile 中，不能只修改顶层 `buttonBindings`。脚本会同时写入设备 profile 和应用注册表，并按设备 ID 前缀更新已有 profile。

组合动作由 SayAll 的本地宏库保存。该库使用两个快捷键步骤：

```text
Command+A
Delete
```

脚本使用固定的本地宏 ID 和快捷键 ID，重复运行时会更新本工作流自己的条目，不会重复追加“全选删除内容”动作。

## 排错

验证配置：

```bash
python3 apply-config.py --verify-only
```

查看无线麦日志：

```bash
tail -50 ~/Library/Logs/RemoteMic/runtime.log
```

常见日志前缀：

- `HID BUTTON`：遥控器按键
- `APP ACTION`：打开或切换 App
- `MACRO`：组合动作执行
- `TRANSCRIPT CAPTURE`：语音转录

如果重新配对了遥控器，设备 ID 可能变化；重新运行脚本并传入新的设备 ID 前缀：

```bash
python3 apply-config.py --device <新设备ID前缀>
```
