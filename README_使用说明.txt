Garry’s Mod LegacySteam — Test3
适用目标：用户提供的 2026 年 10 月 3 日 GMod 正式版文件 + 2024 年 11 月 Steam，Win7。

Test3 修复：适配初始化的已知接口版本检查，并同时为原版 SDK 内部的 SteamClient017 获取路径提供新旧接口转换。模拟测试已增加内部接口路径和多字符串版本检查。可从 Test1/Test2 直接升级。

保留前版修复：将原版 API 声明为直接 DLL 依赖，修正 Win7 首次解析转发入口时出现的“找不到指定的程序”错误。安装脚本可从 Test1/Test2 直接升级，并兼容旧版 .NET，以及根目录/子目录两种放置方式。

这是兼容测试包。测试者已确认在 Windows 7 + 2024 年 11 月 Steam 下，32/64 位游戏均可启动，单人、联机、覆盖层、模组下载和使用正常；创意工坊下载可能还需配合 Zstd 下载补丁。已知问题：游戏内插件列表及“我的订阅”的预览图不显示。结果仅针对这组测试环境。

安装
1. 完全退出 Garry’s Mod，Steam 保持正常运行。
2. 将整个 GMod-LegacySteam-Test3 文件夹放进游戏目录，与 gmod.exe、gmod_win64.exe、bin 文件夹并列。
   示例：D:\SteamLibrary\steamapps\common\GarrysMod\GMod-LegacySteam-Test3\Install.cmd
3. 双击 Install.cmd。看到 TEST3 installed 后，从 Steam 按原来的方式启动游戏。
4. 如果进了主菜单，先测试单人地图，再检查已订阅创意工坊模组是否出现。

创意工坊下载提示
本包适配游戏 Steamworks 接口，不包含 Steam 客户端的 Zstd 下载支持。下载采用 Zstd 压缩的创意工坊内容时，旧版 Steam 可能还需配合 SteamLegacyZstd / Old Steam VSZa Launcher：
https://github.com/yuyu107/SteamLegacyZstd
请按该项目说明使用，并确认其支持你的客户端版本。是否需要取决于下载内容的压缩格式。

反馈
无论成功还是失败，请反馈是否进了主菜单，以及游戏根目录的 GMod-LegacySteam.log。
若有新报错，请把完整报错文本/截图一起发来。
若直接闪退，请同时附上 Windows 事件查看器“Windows 日志 → 应用程序”中对应 Application Error 的故障模块、异常代码和故障偏移。
日志会追加；重复测试可先将旧日志改名，以便区分每次启动。

恢复
退出游戏，双击 Restore.cmd，恢复两份原版游戏 Steam API 库。备份会保留。
本包会在 bin 下保存 steam_api_original.dll，在 bin\win64 下保存 steam_api64_original.dll。
不要删除或改名这两份备份，兼容库正常运行也需要它们。
游戏更新/验证完整性可能把兼容库覆盖；脚本遇到不同版本文件会拒绝替换，不要强行覆盖。

本版做了什么
- 在游戏进程中为旧客户端登记 SteamClient023 兼容接口，重新排列旧 SteamClient021 的函数入口。
- SteamFriends018 通过 SteamFriends017 转发，并纠正删除函数造成的入口位移。
- SteamApps009 通过旧 Apps008 转发已有功能。
- SteamUGC021 通过 UGC020 转发已有功能，处理订阅查询多出的 bool 参数，避免 32 位栈不平衡。
- SteamRemotePlay004 转发旧 RemotePlay002 已有的会话和邀请功能。
- 原版 Steam API 的导出名称/序号保留，已有回调与初始化主要交给原版库处理。
- 不需要安装新的 VC/UCRT；兼容库仅导入 Windows 自带的 KERNEL32、ADVAPI32、USER32。
- Steam 安装目录和磁盘上的 steamclient DLL 不做修改。

本版限制
- 新增的测试分支枚举/切换、游戏性能设置、创意工坊本地禁用/排序/新增下载查询，以及新版远程游玩直接输入等功能，旧客户端没有完整对应实现。本版返回不支持/空结果。
- 创意工坊新查询的“包含本地禁用项”参数暂按旧版查询行为处理。
- 尚未验证所有服务及其他客户端/游戏版本组合；成就等未单独确认的功能需要继续实测。
- 只针对发来的这组二进制文件；客户端接口工厂代码不同会停止初始化并记录日志。
- 本包没有包含游戏原版 DLL、Steam 客户端 DLL；不会伪造游戏所有权或登录状态。

源码在 source 文件夹。verify_bridge.py 需要 Python、pefile、unicorn，用模拟 Win32/Steam 后端验证编译后 DLL 的调用约定、接口路由和参数转发。它不测试真实 Steam IPC。
