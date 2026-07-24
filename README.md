# xorriso-gui

基于 PySide6 的 [xorriso](https://www.gnu.org/software/xorriso/) 图形前端，灵感来自 K3b。

专为解决 K3b 无法续刻 BD-R 蓝光光盘的问题。利用 xorriso 的 `-dev` 模式（growing）实现多 session 追加写入。同时支持新建 ISO、刻录到光盘、光盘对拷、文件提取等完整工作流。

## 安装


```bash
# 解压后一键安装（自动安装依赖 + 生成桌面入口）
./install.sh

# 或使用 Makefile
make deps        # 仅安装 Python 依赖
make install     # deps + 生成桌面文件并安装到 ~/.local/share/
make uninstall   # 卸载桌面入口
make clean       # 清理构建产物
```

`install.sh` 和 `make install` 从 `xorriso-gui.desktop.in` 模板生成桌面文件，自动填入当前目录路径，无需手动修改。

## 运行

```bash
python3 main.py
# 或
make run
```

## 功能

### 界面

- **双面板文件管理器** — 左侧本地文件系统（QFileSystemModel），右侧 ISO/光盘内容
- **传输按钮** — 工具栏 `←` `→` `🗑` 快速完成添加、提取、删除操作
- **驱动器扫描** — 自动发现系统光驱，支持手动输入路径或浏览选择 ISO 文件
- **光盘空间显示** — 加载光盘后状态栏显示已用/可用空间
- **实时日志** — 暗色主题日志面板，xorriso 输出着色分类
- **异步 I/O** — 驱动器扫描、光盘加载、空间查询均在后台 QThread 运行，界面无卡顿

### 拖拽与右键菜单

- **拖拽操作** — 从左面板拖文件到右面板，自动加入任务队列
- **左面板右键** — 添加至 ISO / 新建文件夹 / 刷新 / 在终端打开
- **右面板右键** — 新建文件夹 / 删除 / 重命名 / 提取到磁盘
- **空文件夹占位符** — 空目录显示 `——（空文件夹）——` 灰色占位，方便点选和拖放

### 预览模式

- **预览按钮** — 工具栏切换开关
- **预览 ON**：右侧面板即时显示所有待执行操作的最终效果。创建文件夹后立即可见，可继续往里面拖文件，逐层操作全程可见。
- **预览 OFF**：右侧显示光盘/ISO 实际内容，任务仅在下部队列列表。

### 先规划后执行

- 所有操作加入任务队列，不立即执行
- 点击 **▶ 执行** 弹出确认对话框，显示完整 xorriso 命令行
- 确认后才运行，避免误操作
- 执行成功后自动清空任务队列

### 续刻模式

- 默认开启，加载光盘时自动识别
- 对已有光盘追加新 session（BD-R / DVD-R 等）
- 加载 ISO 文件时自动关闭
- 新建空 ISO 时自动关闭

## 工作流

| 场景 | 操作 |
|------|------|
| 新建 ISO 到文件 | 新建空ISO → 拖入文件 → 输出框填文件路径 → 执行 |
| 直接刻录到光盘 | 输出框选 `/dev/sr0` → 拖入文件 → 执行 |
| 续刻/追加文件 | 加载光盘 → 拖入新文件 → 执行（自动使用 `-dev` 模式） |
| 光盘对拷 | 输入选源盘 → 输出选目标盘 → 执行 |
| 光盘→ISO 复制 | 加载光盘 → 输出填 `.iso` 路径 → 执行 |
| 提取文件 | 加载 ISO/光盘 → 右键"提取到磁盘" → 选目录 |

## 生成命令对照

| 场景 | xorriso 命令 |
|------|-------------|
| 新建 ISO | `-outdev /path/output.iso -iso_rr_pattern off -map ... -commit` |
| 续刻光盘 | `-dev /dev/sr0 -iso_rr_pattern off -rm_r ... -map ... -commit` |
| 光盘对拷 | `-indev /dev/sr0 -outdev /dev/sr1 -iso_rr_pattern off -commit` |
| 光盘→文件 | `-indev /dev/sr0 -outdev /path/copy.iso -iso_rr_pattern off -commit` |

所有命令自动包含 `-iso_rr_pattern off`，确保含 `[ ] * ?` 等特殊字符的文件名正常处理。

## 使用说明

### 工具栏布局

```
第1行: [输入驱动器/文件: ___] [刷新] [浏览] [加载]  [输出到: ___] [新建空ISO] [续刻模式] [预览模式]
第2行: [←] [→] [🗑]  卷标: [___]  [刻录ISO] [TOC] [检查介质]
```

### 按钮速查

| 按钮 | 功能 |
|------|------|
| **刷新** | 扫描系统光驱 |
| **浏览** | 选择 .iso 文件 |
| **加载** | 读取光盘/ISO 内容到右侧面板 |
| **新建空ISO** | 创建空白 ISO 映像，自动开启预览模式 |
| **续刻模式** | 开启后对同一光盘追加 session（BD-R/DVD-R） |
| **预览模式** | 右侧面板即时显示所有待执行操作的最终效果 |
| **←** | 提取右侧选中文件到左侧当前目录 |
| **→** | 添加左侧选中文件到右侧当前目录 |
| **🗑** | 删除右侧选中文件 |
| **刻录ISO** | 打开对话框，将已有 .iso 刻录到光盘 |
| **TOC** | 查看光盘会话表（Table of Contents） |
| **检查介质** | 扫描光盘坏块（最长 30 分钟） |
| **▶ 执行** | 确认 xorriso 命令后执行所有任务 |

### 操作流程

1. 新建或加载 ISO/光盘
2. 拖拽文件或使用箭头按钮添加/删除
3. 所有操作先入任务队列，不立即执行
4. 确认无误后点击 **▶ 执行**，弹出对话框显示完整 xorriso 命令
5. 确认后执行，日志面板实时显示进度

### 右键菜单

- **左面板（磁盘）**：添加至 ISO / 对 .iso 文件: 作为输入ISO镜像打开 / 新建文件夹 / 刷新 / 在终端打开
- **右面板（ISO）**：新建文件夹 / 删除 / 重命名 / 提取到磁盘

---

## AppImage 打包

### 环境要求

- 系统已安装 `xorriso` ≥ 1.5.0
- Python 3.14 + PySide6 6.11（开发时）
- [appimagetool](https://github.com/AppImage/AppImageKit/releases)（制作 .AppImage）

### 构建步骤

```bash
# 方式 1: Makefile
make appimage

# 方式 2: 手动
python3.14 -m pip install pyinstaller
./build_appimage.sh
```

产出: build_appimage/xorriso-gui-YYYYMMDD-x86_64.AppImage

构建脚本会自动：
1. `pyinstaller --onedir --collect-all PySide6` 打包 Python 应用
2. 组装 AppDir 结构（AppRun + .desktop + icon）
3. 调用 `appimagetool` 生成 .AppImage

### 在桌面环境中注册

```bash
cp build_appimage/xorriso-gui-*.AppImage ~/.local/bin/xorriso-gui
cp xorriso-gui.desktop ~/.local/share/applications/
cp xorriso_gui/assets/icon.svg ~/.local/share/icons/xorriso-gui.svg
```

---

## 依赖

- Python 3.11+（构建需 Python 3.14）
- [PySide6](https://pypi.org/project/PySide6/) ≥ 6.5.0
- [PyInstaller](https://pyinstaller.org/)（仅打包时）
- [xorriso](https://www.gnu.org/software/xorriso/) ≥ 1.5.0（运行时）

## 项目结构

```
xorriso-gui/
├── main.py                      # 入口
├── requirements.txt
└── xorriso_gui/
    ├── app.py                   # QApplication 启动
    ├── main_window.py           # 主窗口：双面板 + 工具栏 + 任务队列 + 预览逻辑
    ├── engine/
    │   ├── xorriso_process.py   # QProcess 异步包装
    │   ├── drive_manager.py     # 驱动器扫描、TOC 解析、介质空间查询
    │   ├── iso_reader.py        # xorriso -find 输出 → 文件树 + 占位符
    │   ├── task_builder.py      # 任务队列 → xorriso 命令行
    │   └── workers.py           # QThread 后台 IO 线程（扫描/加载/空间查询）
    ├── models/
    │   ├── file_tree_model.py   # QAbstractItemModel 文件树 + FileNode.clone()
    │   └── task_item.py         # TaskItem / TaskType 数据结构
    ├── widgets/
    │   ├── disk_panel.py        # 左面板：QFileSystemModel 磁盘浏览器 + 右键菜单
    │   ├── iso_panel.py         # 右面板：ISO/光盘浏览器 + 拖放 + 右键菜单
    │   ├── file_tree_view.py    # 可拖拽 QTreeView 基类
    │   ├── task_queue_widget.py # 任务队列面板（操作/源/目标 三列）
    │   └── log_viewer.py        # 暗色主题着色日志
    └── utils/
        └── settings.py          # QSettings 持久化
```

## License

GPL-3.0-or-later（与 xorriso 保持一致）
