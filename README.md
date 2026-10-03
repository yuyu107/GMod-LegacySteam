# GMod-LegacySteam

让 Garry’s Mod 通过 Steamworks 兼容桥接使用 2024 年 11 月的旧版 Steam，支持 Windows 7 下的 32 位与 64 位游戏。

当前版本：**v0.1.0-test3（测试版）**。

## 实测状态

测试环境为 Windows 7、2024 年 11 月 Steam、2026 年 9 月 17 日版本的 Garry’s Mod 正式分支（2026 年 10 月 3 日提供的二进制文件）。测试者反馈：32 位与 64 位均能启动，单人、联机、覆盖层以及模组下载和使用正常。这些结果来自该环境，不保证其他版本组合兼容。

**已知问题：游戏内插件列表及“我的订阅”的模组预览图不显示，标题、作者等信息仍显示。尚未确定原因。**

## 安装

1. 下载本仓库：绿色 Code → Download ZIP，并解压。
2. 完全退出 Garry’s Mod，把解压出的整个文件夹放进游戏根目录，与 `gmod.exe`、`gmod_win64.exe` 和 `bin` 并列。
3. 双击文件夹里的 `Install.cmd`。Steam 保持正常运行，安装成功后从 Steam 启动游戏。

安装器同时处理 32 位和 64 位库，支持 Windows 7 自带的旧版 PowerShell/.NET。安装前校验原版文件及备份，可从此前 Test1/Test2 升级。

原版库备份为 `bin/steam_api_original.dll` 与 `bin/win64/steam_api64_original.dll`。运行兼容桥也需要这两份文件，**不要删除或改名**。

## 还原与游戏更新

退出游戏，运行 `Restore.cmd` 恢复原版库，备份保留。游戏更新或验证完整性可能覆盖补丁。安装器针对本次测试的原版文件哈希，不同文件会拒绝替换，不要强行覆盖；更新后需要重新评估适配。

## 工作原理与限制

在游戏进程内登记兼容接口，并适配 SteamClient023、SteamFriends018、SteamApps009、SteamUGC021 和 SteamRemotePlay004 的旧接口调用。保留原版 Steam API 的导出名称与序号，回调和已有功能继续交给原版库；适配内部 SteamClient017 获取路径与初始化版本检查。

旧客户端缺少的新功能返回不支持或空结果，包括部分测试分支管理、游戏性能设置、创意工坊本地禁用/排序及新增下载查询、远程游玩直接输入等。UGC 查询中的“包含本地禁用项”参数按旧客户端行为处理。

仅修改游戏 API 库，不修改磁盘上的 Steam 客户端文件。无需扩展内核或新增 VC/UCRT 依赖。本项目不提供游戏文件，不改变游戏所有权与登录状态，需使用正常的 Steam 登录和游戏授权。

## 构建与验证

源码与构建说明位于 `source/`。使用 Zig 0.16.0 构建，详见 [BUILD.txt](source/BUILD.txt)。

```sh
python -m pip install pefile unicorn
python source/verify_bridge.py
```

验证脚本在模拟 Win32/Steam 后端中执行编译后的 x86/x64 DLL，检查接口路由、参数传递、调用约定与栈平衡，不替代真实 Steam IPC 和游戏测试。

## 问题反馈

请提供系统版本、Steam 客户端版本、GMod 版本及启动位数，并附上完整报错和游戏根目录的 `GMod-LegacySteam.log`。日志会追加，可先改名旧日志再复现。不要提交账户凭据或个人敏感信息。

## 许可证

项目自编写代码采用 [MIT License](LICENSE)。Steam 与 Garry’s Mod 属于各自权利人，仓库不包含原版游戏 DLL、Steam 客户端 DLL 或 Steamworks SDK。
