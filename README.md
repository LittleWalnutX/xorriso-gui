# xorriso-gui

基于 PySide6 的 [xorriso](https://www.gnu.org/software/xorriso/) 图形前端，灵感来自 K3b。

专为解决 K3b 无法续刻 BD-R 蓝光光盘的问题。利用 xorriso 的 `-dev` 模式（growing）实现多 session 追加写入。

## 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 确保系统已安装 xorriso
which xorriso
```

## 运行

```bash
python3 main.py
```

## 功能

- **双面板文件管理器** — 左侧本地文件系统，右侧 ISO/光盘内容
- **拖拽操作** — 从左侧拖拽文件到右侧（加入任务队列），右键菜单删除/重命名/提取
- **先规划后执行** — 所有操作先排队，点击"执行"时弹出确认对话框，显示完整 xorriso 命令行
- **续刻模式（growing）** — 对已有光盘追加新 session（BD-R/DVD-R 等）
- **驱动器扫描** — 自动发现系统光驱，支持手动输入路径或 ISO 文件
- **实时日志** — 着色显示 xorriso stdout/stderr 输出

## 工作流

| 场景 | 操作 |
|------|------|
| 新建 ISO | 右侧创建空白 ISO → 从左侧拖入文件 → 指定输出文件/设备 → 执行 |
| 直接刻录到光盘 | 选择光盘设备作为输出 → 拖入文件 → 执行 |
| 续刻/追加 | 选择已有光盘 → 加载 → 拖入新文件 → 执行 |
| 光盘复制 | 输入驱动器选源盘 → 输出驱动器选目标 → 执行 |
| 提取文件 | 加载 ISO → 右键"提取到磁盘" → 选择目标目录 |

## 依赖

- Python 3.8+
- [PySide6](https://pypi.org/project/PySide6/) ≥ 6.5.0
- [xorriso](https://www.gnu.org/software/xorriso/) ≥ 1.5.0

## 项目结构

```
xorriso-gui/
├── main.py                      # 入口
├── requirements.txt
└── xorriso_gui/
    ├── app.py                   # QApplication
    ├── main_window.py           # 主窗口：双面板 + 工具栏 + 任务队列
    ├── engine/
    │   ├── xorriso_process.py   # QProcess 异步包装
    │   ├── drive_manager.py     # 驱动器扫描、TOC 解析
    │   ├── iso_reader.py        # 解析 xorriso -find 输出为文件树
    │   └── task_builder.py      # 任务队列 → xorriso 命令行
    ├── models/
    │   ├── file_tree_model.py   # QAbstractItemModel 文件树
    │   └── task_item.py         # 任务数据结构
    ├── widgets/
    │   ├── disk_panel.py        # 左面板：本地磁盘浏览器
    │   ├── iso_panel.py         # 右面板：ISO/光盘浏览器 + 拖放
    │   ├── file_tree_view.py    # 可拖拽 QTreeView
    │   ├── task_queue_widget.py # 任务队列面板
    │   └── log_viewer.py        # 着色日志输出
    └── utils/
        └── settings.py          # QSettings
```

## License

GPL-3.0-or-later（与 xorriso 保持一致）