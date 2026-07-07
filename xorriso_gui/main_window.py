from PySide6.QtWidgets import (QMainWindow, QSplitter, QToolBar, QStatusBar,
                                QVBoxLayout, QWidget, QComboBox, QPushButton,
                                QMessageBox, QLabel, QHBoxLayout, QTabWidget,
                                QFileDialog, QApplication)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

from xorriso_gui.engine.drive_manager import scan_drives, get_toc, DriveInfo
from xorriso_gui.engine.iso_reader import load_iso_contents, load_empty_iso
from xorriso_gui.engine.task_builder import TaskBuilder
from xorriso_gui.engine.xorriso_process import XorrisoProcess
from xorriso_gui.models.task_item import TaskItem, TaskType
from xorriso_gui.models.file_tree_model import FileTreeModel, FileNode
from xorriso_gui.widgets.disk_panel import DiskPanel
from xorriso_gui.widgets.iso_panel import IsoPanel
from xorriso_gui.widgets.task_queue_widget import TaskQueueWidget
from xorriso_gui.widgets.log_viewer import LogViewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("xorriso-gui — ISO 镜像管理器")
        self.resize(1100, 700)

        self._tasks = []
        self._current_drive_path = None
        self._output_path = None
        self._is_disc_mode = False
        self._pending_args = []
        self._pending_display = ""

        self._xorriso = XorrisoProcess(self)
        self._xorriso.ready_read_stdout.connect(self._on_stdout)
        self._xorriso.ready_read_stderr.connect(self._on_stderr)
        self._xorriso.finished.connect(self._on_process_finished)

        self._init_ui()
        self._refresh_drives()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self._init_toolbar(main_layout)
        self._init_main_content(main_layout)
        self._init_statusbar()

    def _init_toolbar(self, main_layout):
        tb_layout = QHBoxLayout()

        tb_layout.addWidget(QLabel("输入驱动器/文件:"))

        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(250)
        self.drive_combo.setEditable(True)
        self.drive_combo.setToolTip("选择输入驱动器、ISO文件路径，或留空新建ISO")
        tb_layout.addWidget(self.drive_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh_drives)
        tb_layout.addWidget(self.refresh_btn)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_iso)
        tb_layout.addWidget(self.browse_btn)

        self.load_btn = QPushButton("加载")
        self.load_btn.clicked.connect(self._load_drive)
        tb_layout.addWidget(self.load_btn)

        tb_layout.addSpacing(20)

        tb_layout.addWidget(QLabel("输出到:"))

        self.output_combo = QComboBox()
        self.output_combo.setMinimumWidth(200)
        self.output_combo.setEditable(True)
        self.output_combo.setToolTip("输出目标（设备路径或ISO文件路径）")
        tb_layout.addWidget(self.output_combo)

        self.new_iso_btn = QPushButton("新建空ISO")
        self.new_iso_btn.clicked.connect(self._new_empty_iso)
        tb_layout.addWidget(self.new_iso_btn)

        self.disc_mode_btn = QPushButton("续刻模式")
        self.disc_mode_btn.setToolTip("直接对光盘续刻（-dev模式）")
        self.disc_mode_btn.clicked.connect(self._toggle_disc_mode)
        tb_layout.addWidget(self.disc_mode_btn)

        tb_layout.addStretch()

        main_layout.addLayout(tb_layout)

    def _init_main_content(self, main_layout):
        self.splitter = QSplitter(Qt.Horizontal)

        self.disk_panel = DiskPanel(self)
        self.iso_panel = IsoPanel(self)

        self.splitter.addWidget(self.disk_panel)
        self.splitter.addWidget(self.iso_panel)
        self.splitter.setSizes([500, 500])

        self._connect_panel_signals()

        main_layout.addWidget(self.splitter, stretch=1)

        self.task_queue = TaskQueueWidget(self)
        self.task_queue.execute_requested.connect(self._on_execute_clicked)
        self.task_queue.clear_requested.connect(self._on_clear_tasks)

        self.log_viewer = LogViewer(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.task_queue, "任务队列")
        self.tab_widget.addTab(self.log_viewer, "日志输出")

        bottom_splitter = QSplitter(Qt.Vertical)
        bottom_splitter.addWidget(self.tab_widget)
        bottom_splitter.setSizes([140])
        bottom_splitter.setMaximumHeight(220)

        main_layout.addWidget(bottom_splitter, stretch=0)

    def _connect_panel_signals(self):
        self.iso_panel.prepare_add.connect(self._on_add_to_iso)
        self.iso_panel.prepare_remove.connect(self._on_remove_from_iso)
        self.iso_panel.prepare_rename.connect(self._on_rename_in_iso)
        self.iso_panel.prepare_extract.connect(self._on_extract_from_iso)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _refresh_drives(self):
        self.status_bar.showMessage("扫描驱动器...")
        self.drive_combo.clear()
        self.output_combo.clear()

        drives = scan_drives()
        for d in drives:
            self.drive_combo.addItem(d.display_name(), d.path)
            self.output_combo.addItem(d.display_name(), d.path)

        if drives:
            self.status_bar.showMessage(f"发现 {len(drives)} 个驱动器")
        else:
            self.drive_combo.setEditText("")
            self.output_combo.setEditText("")
            self.status_bar.showMessage("未发现光驱，可手动输入路径或ISO文件")

    def _browse_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 ISO 镜像文件", "",
            "ISO 镜像 (*.iso *.ISO);;所有文件 (*)"
        )
        if path:
            self.drive_combo.setEditText(path)

    def _load_drive(self):
        path = self.drive_combo.currentText()
        data = self.drive_combo.currentData()
        if data:
            path = data

        if not path:
            self.log_viewer.append_info("请选择或输入一个驱动器或ISO文件路径")
            return

        self.status_bar.showMessage(f"正在加载 {path} ...")
        QApplication.processEvents()

        root, error = load_iso_contents(drive_path=path)
        if error:
            self.log_viewer.append_error(f"加载失败: {error}")
            self.status_bar.showMessage(f"加载失败: {error}")
        else:
            self.iso_panel.load_contents(root)
            self.log_viewer.append_info(f"已加载: {path}")
            self.status_bar.showMessage(f"已加载: {path}")

    def _new_empty_iso(self):
        root = load_empty_iso()
        self.iso_panel.load_contents(root)
        self.drive_combo.setEditText("")
        self.log_viewer.append_info("已创建新的空白 ISO 映像")
        self.status_bar.showMessage("新的空白 ISO 映像")

    def _toggle_disc_mode(self):
        self._is_disc_mode = not self._is_disc_mode
        if self._is_disc_mode:
            self.disc_mode_btn.setText("续刻模式 ✓")
            self.disc_mode_btn.setStyleSheet(
                "QPushButton { background-color: #e67e22; color: white; }"
            )
            self.log_viewer.append_info("已启用续刻模式：输入和输出使用同一光盘（-dev）")
        else:
            self.disc_mode_btn.setText("续刻模式")
            self.disc_mode_btn.setStyleSheet("")
            self.log_viewer.append_info("已退出续刻模式")

    def _on_add_to_iso(self, local_path, iso_path):
        task = TaskItem(TaskType.MAP, source=local_path, target=iso_path,
                        description=f"添加 {local_path} → {iso_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(f"已加入任务: +添加 {local_path} → {iso_path}")

    def _on_remove_from_iso(self, iso_path):
        task = TaskItem(TaskType.REMOVE, target=iso_path,
                        description=f"删除 {iso_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(f"已加入任务: -删除 {iso_path}")

    def _on_rename_in_iso(self, old_path, new_path):
        task = TaskItem(TaskType.RENAME, source=old_path, target=new_path,
                        description=f"重命名 {old_path} → {new_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(f"已加入任务: 重命名 {old_path} → {new_path}")

    def _on_extract_from_iso(self, iso_path, dest_path):
        task = TaskItem(TaskType.EXTRACT, source=iso_path, target=dest_path,
                        description=f"提取 {iso_path} → {dest_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(f"已加入任务: 提取 {iso_path} → {dest_path}")

    def _on_clear_tasks(self):
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有任务吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._tasks.clear()
            self.task_queue.clear_all()
            self.log_viewer.append_info("任务队列已清空")

    def _on_execute_clicked(self):
        if not self._build_and_confirm():
            return
        self._run_xorriso()

    def _build_and_confirm(self):
        builder = TaskBuilder()

        input_drive = self.drive_combo.currentText().strip()
        output_drive = self.output_combo.currentText().strip()

        output_data = self.output_combo.currentData()
        if output_data:
            output_drive = output_data

        if self._is_disc_mode:
            if not input_drive:
                QMessageBox.warning(self, "错误", "续刻模式下必须指定一个光盘设备。")
                return False
            builder.set_same_drive(input_drive)
        else:
            input_data = self.drive_combo.currentData()
            if input_data:
                input_drive = input_data

            if input_drive:
                builder.set_input_drive(input_drive)
            if output_drive:
                builder.set_output_drive(output_drive)
                if not input_drive:
                    builder.set_output_drive(output_drive)

        if not output_drive and not input_drive:
            QMessageBox.warning(self, "错误", "请指定输出目标（设备或ISO文件路径）。")
            return False

        args = builder.build_args(self._tasks)
        display = builder.args_to_display(args)

        msg = QMessageBox(self)
        msg.setWindowTitle("确认执行 xorriso 命令")
        msg.setIcon(QMessageBox.Question)
        msg.setText("即将执行以下 xorriso 命令：")
        msg.setDetailedText(display)

        cmd_preview = display[:200] + ("..." if len(display) > 200 else "")
        msg.setInformativeText(cmd_preview)

        run_btn = msg.addButton("▶ 执行", QMessageBox.AcceptRole)
        cancel_btn = msg.addButton("取消", QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)

        msg.exec()

        if msg.clickedButton() == run_btn:
            self._pending_args = args
            self._pending_display = display
            return True
        return False

    def _run_xorriso(self):
        args = self._pending_args
        display = self._pending_display
        self.log_viewer.append_info("=" * 60)
        self.log_viewer.append_info(f"执行命令: {display}")
        self.log_viewer.append_info("=" * 60)

        self.status_bar.showMessage("正在执行 xorriso ...")
        QApplication.processEvents()

        self._xorriso.run(args)

    def _on_stdout(self, text):
        self.log_viewer.append_stdout(text)

    def _on_stderr(self, text):
        self.log_viewer.append_stderr(text)

    def _on_process_finished(self, exit_code):
        if exit_code == 0:
            self.log_viewer.append_success(f"执行成功 (exit code: {exit_code})")
            self.status_bar.showMessage("执行成功")
            if not self._is_disc_mode:
                QTimer.singleShot(500, self._reload_iso_after_commit)
        else:
            self.log_viewer.append_error(f"执行失败 (exit code: {exit_code})")
            self.status_bar.showMessage(f"执行失败, exit code: {exit_code}")

    def _reload_iso_after_commit(self):
        self.status_bar.showMessage("重新加载 ISO 内容...")
        output = self.output_combo.currentText().strip()
        output_data = self.output_combo.currentData()
        if output_data:
            output = output_data
        if output:
            root, error = load_iso_contents(drive_path=output)
            if not error:
                self.iso_panel.load_contents(root)
                self.status_bar.showMessage(f"已重新加载: {output}")
            else:
                self.status_bar.showMessage(f"重新加载失败: {error}")