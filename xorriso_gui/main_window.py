import os
import subprocess

from PySide6.QtWidgets import (QMainWindow, QSplitter, QToolBar, QStatusBar,
                                QVBoxLayout, QWidget, QComboBox, QPushButton,
                                QMessageBox, QLabel, QHBoxLayout, QTabWidget,
                                QFileDialog, QApplication, QLineEdit, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QEvent, QObject
from PySide6.QtGui import QAction, QIcon

from xorriso_gui.engine.workers import ScanDrivesWorker, LoadIsoWorker, MediaSpaceWorker
from xorriso_gui.engine.iso_reader import load_empty_iso
from xorriso_gui.engine.task_builder import TaskBuilder
from xorriso_gui.engine.xorriso_process import XorrisoProcess
from xorriso_gui.models.task_item import TaskItem, TaskType
from xorriso_gui.models.file_tree_model import FileTreeModel, FileNode
from xorriso_gui.widgets.disk_panel import DiskPanel
from xorriso_gui.widgets.iso_panel import IsoPanel
from xorriso_gui.widgets.task_queue_widget import TaskQueueWidget
from xorriso_gui.widgets.log_viewer import LogViewer
from xorriso_gui.widgets.burn_iso_dialog import BurnIsoDialog
from xorriso_gui.widgets.toc_dialog import TocDialog
from xorriso_gui.i18n import tr, set_language, languages, get_language


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("xorriso-gui — ISO 镜像管理器")
        self.resize(1100, 700)

        self._tasks = []
        self._current_drive_path = None
        self._output_path = None
        self._is_disc_mode = True
        self._preview_mode = False
        self._actual_root = load_empty_iso()
        self._pending_args = []
        self._pending_display = ""

        self._xorriso = XorrisoProcess(self)
        self._xorriso.ready_read_stdout.connect(self._on_stdout)
        self._xorriso.ready_read_stderr.connect(self._on_stderr)
        self._xorriso.finished.connect(self._on_process_finished)

        self._init_ui()
        self._apply_translations()
        self._refresh_drives()

        if self._is_disc_mode:
            self.disc_mode_btn.setStyleSheet(
                "QPushButton { background-color: #e67e22; color: white; }"
            )

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self._init_toolbar(main_layout)
        self._init_main_content(main_layout)
        self._init_statusbar()

    def _init_toolbar(self, main_layout):
        tb_wrapper = QVBoxLayout()
        tb_wrapper.setSpacing(4)

        row1 = QHBoxLayout()
        row1.addStretch()

        row1.addWidget(QLabel("输入驱动器/文件:"))
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(150)
        self.drive_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.drive_combo.setEditable(True)
        self.drive_combo.setToolTip("选择输入驱动器、ISO文件路径，或留空新建ISO")
        row1.addWidget(self.drive_combo, stretch=2)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh_drives)
        row1.addWidget(self.refresh_btn)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_iso)
        row1.addWidget(self.browse_btn)

        self.load_btn = QPushButton("加载")
        self.load_btn.clicked.connect(self._load_drive)
        row1.addWidget(self.load_btn)

        row1.addSpacing(16)

        row1.addWidget(QLabel("输出到:"))
        self.output_combo = QComboBox()
        self.output_combo.setMinimumWidth(150)
        self.output_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.output_combo.setEditable(True)
        self.output_combo.setToolTip("输出目标（设备路径或ISO文件路径）")
        row1.addWidget(self.output_combo, stretch=2)

        self.new_iso_btn = QPushButton("新建空ISO")
        self.new_iso_btn.clicked.connect(self._new_empty_iso)
        row1.addWidget(self.new_iso_btn)

        self.disc_mode_btn = QPushButton("续刻模式")
        self.disc_mode_btn.setToolTip("直接对光盘续刻（-dev模式）")
        self.disc_mode_btn.clicked.connect(self._toggle_disc_mode)
        row1.addWidget(self.disc_mode_btn)

        self.preview_btn = QPushButton("预览模式")
        self.preview_btn.setToolTip("在右侧面板中即时预览所有待执行操作的最终效果")
        self.preview_btn.clicked.connect(self._toggle_preview)
        row1.addWidget(self.preview_btn)

        row1.addStretch()
        tb_wrapper.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addStretch()

        self.left_arrow_btn = QPushButton("←")
        self.left_arrow_btn.setToolTip("将右侧选中的文件提取到左侧当前目录")
        self.left_arrow_btn.setFixedWidth(32)
        self.left_arrow_btn.clicked.connect(self._on_transfer_left)
        row2.addWidget(self.left_arrow_btn)

        self.right_arrow_btn = QPushButton("→")
        self.right_arrow_btn.setToolTip("将左侧选中的文件添加到右侧当前目录")
        self.right_arrow_btn.setFixedWidth(32)
        self.right_arrow_btn.clicked.connect(self._on_transfer_right)
        row2.addWidget(self.right_arrow_btn)

        self.trash_btn = QPushButton("🗑")
        self.trash_btn.setToolTip("删除右侧选中的文件")
        self.trash_btn.setFixedWidth(32)
        self.trash_btn.clicked.connect(self._on_trash)
        row2.addWidget(self.trash_btn)

        row2.addSpacing(16)
        row2.addWidget(QLabel("卷标:"))
        self.volume_id_edit = QLineEdit()
        self.volume_id_edit.setPlaceholderText("(可选)")
        self.volume_id_edit.setMaximumWidth(180)
        self.volume_id_edit.setToolTip("ISO 卷标名（Volume ID）")
        row2.addWidget(self.volume_id_edit)

        row2.addSpacing(16)

        self.lang_combo = QComboBox()
        self.lang_combo.setMaximumWidth(70)
        self.lang_combo.setToolTip("界面语言 / Language")
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("日本語", "ja")
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        row2.addWidget(self.lang_combo)

        row2.addSpacing(16)

        self.burn_iso_btn = QPushButton("刻录ISO")
        self.burn_iso_btn.setToolTip("将已有的 .iso 文件刻录到光盘")
        self.burn_iso_btn.clicked.connect(self._on_burn_iso_dialog)
        row2.addWidget(self.burn_iso_btn)

        self.toc_btn = QPushButton("TOC")
        self.toc_btn.setToolTip("查看光盘的 Table of Contents 会话信息")
        self.toc_btn.clicked.connect(self._on_toc_dialog)
        row2.addWidget(self.toc_btn)

        self.check_media_btn = QPushButton(tr("check_media.title"))
        self.check_media_btn.setToolTip("扫描光盘介质检查损坏块")
        self.check_media_btn.clicked.connect(self._on_check_media)
        row2.addWidget(self.check_media_btn)

        row2.addStretch()
        tb_wrapper.addLayout(row2)

        main_layout.addLayout(tb_wrapper)

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
        self.task_queue.task_removed.connect(self._on_task_removed)

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
        self.iso_panel.prepare_mkdir.connect(self._on_mkdir_in_iso)
        self.disk_panel.add_to_iso.connect(self._on_add_to_iso)
        self.disk_panel.open_terminal.connect(self._on_open_terminal)
        self.disk_panel.load_iso_file.connect(self._on_load_iso_from_disk)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("status.ready"))

    def _update_media_space(self, path):
        if not path or not path.startswith("/dev/"):
            return
        self._space_worker = MediaSpaceWorker(path, self)
        self._space_worker.result.connect(self._on_media_space)
        self._space_worker.start()

    def _on_media_space(self, path, summary):
        if summary:
            self.status_bar.showMessage(f"📀 {summary}")

    def _refresh_drives(self):
        self.status_bar.showMessage(tr("status.scanning"))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._scan_worker = ScanDrivesWorker(self)
        self._scan_worker.result.connect(self._on_drives_scanned)
        self._scan_worker.start()

    def _on_drives_scanned(self, drives):
        QApplication.restoreOverrideCursor()
        self.drive_combo.clear()
        self.output_combo.clear()
        for d in drives:
            self.drive_combo.addItem(d.display_name(), d.path)
            self.output_combo.addItem(d.display_name(), d.path)
        if drives:
            self.status_bar.showMessage(tr("status.found").format(count=len(drives)))
        else:
            self.status_bar.showMessage(tr("status.no_drives"))

    def _browse_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 ISO 镜像文件", "",
            "ISO 镜像 (*.iso *.ISO);;所有文件 (*)"
        )
        if path:
            self.drive_combo.setEditText(path)

    def _load_drive(self):
        path = _resolve_combo_path(self.drive_combo)

        if not path:
            self.log_viewer.append_info(tr("error.no_input"))
            return

        self.status_bar.showMessage(tr("status.loading").format(path=path))
        QApplication.setOverrideCursor(Qt.WaitCursor)

        if path.startswith("/dev/"):
            self._set_disc_mode(True)
            self.log_viewer.append_info(tr("log.device_path_disc"))
        else:
            self._set_disc_mode(False)
            self.log_viewer.append_info(tr("log.file_path_iso"))

        self._load_worker = LoadIsoWorker(path, self)
        self._load_worker.result.connect(self._on_iso_loaded)
        self._load_worker.start()

    def _on_iso_loaded(self, root, error, volid):
        QApplication.restoreOverrideCursor()
        path = self._load_worker.drive_path
        if error:
            self.log_viewer.append_error(tr("error.load_failed").format(msg=error))
            self.status_bar.showMessage(tr("error.load_failed").format(msg=error))
        else:
            self._actual_root = root.clone()
            self.iso_panel.load_contents(root)
            self.log_viewer.append_info(tr("status.loaded").format(path=path))
            self.status_bar.showMessage(tr("status.loaded").format(path=path))
            self.output_combo.setEditText(path)
            if volid:
                self.volume_id_edit.setText(volid)
            self._update_media_space(path)

    def _new_empty_iso(self):
        root = load_empty_iso()
        self._actual_root = root.clone()
        self.iso_panel.load_contents(root)
        self.drive_combo.setEditText("")
        self._set_disc_mode(False)
        self._set_preview_mode(True)
        self._tasks.clear()
        self.task_queue.clear_all()
        self.log_viewer.append_info(tr("log.new_iso_preview"))
        self.status_bar.showMessage(tr("status.new_empty"))

    def _toggle_disc_mode(self):
        self._set_disc_mode(not self._is_disc_mode)

    def _set_disc_mode(self, enabled):
        self._is_disc_mode = enabled
        if enabled:
            self.disc_mode_btn.setText("续刻模式 ✓")
            self.disc_mode_btn.setStyleSheet(
                "QPushButton { background-color: #e67e22; color: white; }"
            )
        else:
            self.disc_mode_btn.setText("续刻模式")
            self.disc_mode_btn.setStyleSheet("")

    def _toggle_preview(self):
        self._set_preview_mode(not self._preview_mode)

    def _set_preview_mode(self, enabled):
        self._preview_mode = enabled
        if enabled:
            self.preview_btn.setText("预览模式 ✓")
            self.preview_btn.setStyleSheet(
                "QPushButton { background-color: #2e86c1; color: white; }"
            )
        else:
            self.preview_btn.setText("预览模式")
            self.preview_btn.setStyleSheet("")
        self._refresh_display()

    def _refresh_display(self):
        if self._preview_mode:
            self._rebuild_preview()
        else:
            self.iso_panel.load_contents(self._actual_root.clone())

    def _rebuild_preview(self):
        root = self._actual_root.clone()
        for task in self._tasks:
            self._apply_task_to_tree(root, task)
        _add_placeholders_to_tree(root)
        self.iso_panel.load_contents(root)

    def _apply_task_to_tree(self, root, task):
        if task.task_type == TaskType.MAP or task.task_type == TaskType.ADD:
            parent_path, name = _split_iso_path(task.target)
            parent = _find_node(root, parent_path)
            if parent and parent.is_dir:
                _remove_placeholder(parent)
                node = FileNode(name=name, path=task.target, size=0,
                                is_dir=False, mode="-rw-r--r--")
                parent.add_child(node)
                parent.sort_children()
        elif task.task_type == TaskType.MKDIR:
            parent_path, name = _split_iso_path(task.target)
            parent = _find_node(root, parent_path)
            if parent and parent.is_dir:
                _remove_placeholder(parent)
                if not parent.find_child(name):
                    node = FileNode(name=name, path=task.target,
                                    is_dir=True, mode="drwxr-xr-x")
                    parent.add_child(node)
                    parent.sort_children()
        elif task.task_type == TaskType.REMOVE:
            _remove_node_from_tree(root, task.target)
        elif task.task_type == TaskType.RENAME:
            _rename_node_in_tree(root, task.source, task.target)

    def _on_language_changed(self, index):
        lang = self.lang_combo.itemData(index)
        if lang:
            set_language(lang)
            self._apply_translations()
            self._refresh_display()

    def _apply_translations(self):
        self.setWindowTitle(tr("window.title"))

        self.browse_btn.setText(tr("btn.browse"))
        self.browse_btn.setToolTip(tr("tooltip.browse"))
        self.refresh_btn.setText(tr("btn.refresh"))
        self.refresh_btn.setToolTip(tr("tooltip.refresh"))
        self.load_btn.setText(tr("btn.load"))
        self.load_btn.setToolTip(tr("tooltip.load"))
        self.new_iso_btn.setText(tr("btn.new_iso"))
        self.new_iso_btn.setToolTip(tr("tooltip.new_iso"))

        if self._is_disc_mode:
            self.disc_mode_btn.setText(tr("btn.disc_mode_on"))
        else:
            self.disc_mode_btn.setText(tr("btn.disc_mode"))
        self.disc_mode_btn.setToolTip(tr("tooltip.disc_mode"))

        if self._preview_mode:
            self.preview_btn.setText(tr("btn.preview_on"))
        else:
            self.preview_btn.setText(tr("btn.preview"))
        self.preview_btn.setToolTip(tr("tooltip.preview"))

        self.volume_id_edit.setPlaceholderText(tr("placeholder.volume_id"))
        self.volume_id_edit.setToolTip(tr("tooltip.volume_id"))
        self.left_arrow_btn.setToolTip(tr("tooltip.left_arrow"))
        self.right_arrow_btn.setToolTip(tr("tooltip.right_arrow"))
        self.trash_btn.setToolTip(tr("tooltip.trash"))
        self.burn_iso_btn.setText(tr("btn.burn_iso"))
        self.burn_iso_btn.setToolTip(tr("tooltip.burn_iso"))
        self.toc_btn.setText(tr("btn.toc"))
        self.toc_btn.setToolTip(tr("tooltip.toc"))
        self.check_media_btn.setText(tr("btn.check_media"))
        self.check_media_btn.setToolTip(tr("tooltip.check_media"))

        self.task_queue.title_label.setText(tr("tab.tasks"))
        self.task_queue.clear_btn.setText(tr("btn.clear_all"))
        self.task_queue.remove_btn.setText(tr("btn.remove_selected"))
        self.task_queue.execute_btn.setText(tr("btn.execute"))

        self.tab_widget.setTabText(0, tr("tab.tasks"))
        self.tab_widget.setTabText(1, tr("tab.log"))

        self.disk_panel.path_label.setText(tr("panel.disk_filesystem"))
        self.iso_panel.path_label.setText(tr("panel.iso_contents"))

        self.task_queue._update_type_labels()

        self.lang_combo.blockSignals(True)
        current = get_language()
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.blockSignals(False)

        if not self.status_bar.currentMessage():
            self.status_bar.showMessage(tr("status.ready"))

    def _on_add_to_iso(self, local_path, iso_path):
        task = TaskItem(TaskType.MAP, source=local_path, target=iso_path,
                        description=f"添加 {local_path} → {iso_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(tr("log.task_add").format(src=local_path, dst=iso_path))
        self._refresh_display()

    def _on_remove_from_iso(self, iso_path):
        cancelled = 0
        for task in list(self._tasks):
            if task.task_type in (TaskType.MAP, TaskType.ADD, TaskType.MKDIR) \
                    and task.target == iso_path:
                self._tasks.remove(task)
                self._remove_task_from_queue(task)
                cancelled += 1
            elif task.task_type in (TaskType.MAP, TaskType.ADD, TaskType.MKDIR) \
                    and task.target.startswith(iso_path.rstrip("/") + "/"):
                self._tasks.remove(task)
                self._remove_task_from_queue(task)
                cancelled += 1
        if cancelled:
            self.log_viewer.append_info(
                tr("log.task_cancelled").format(count=cancelled, path=iso_path))
            self._refresh_display()
            return

        task = TaskItem(TaskType.REMOVE, target=iso_path,
                        description=f"删除 {iso_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(tr("log.task_remove").format(path=iso_path))
        self._refresh_display()

    def _remove_task_from_queue(self, task):
        tbl = self.task_queue.table
        for row in range(tbl.rowCount()):
            item = tbl.item(row, 0)
            if item and item.data(Qt.UserRole) is task:
                tbl.removeRow(row)
                break

    def _on_rename_in_iso(self, old_path, new_path):
        for task in list(self._tasks):
            if task.task_type in (TaskType.MAP, TaskType.ADD, TaskType.MKDIR) \
                    and task.target == new_path:
                self._tasks.remove(task)
                self._remove_task_from_queue(task)
                self.log_viewer.append_info(
                    tr("log.task_cancelled_rename").format(path=new_path))
                break

        task = TaskItem(TaskType.RENAME, source=old_path, target=new_path,
                        description=f"重命名 {old_path} → {new_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(tr("log.task_rename").format(src=old_path, dst=new_path))
        self._refresh_display()

    def _on_extract_from_iso(self, iso_path, dest_path):
        task = TaskItem(TaskType.EXTRACT, source=iso_path, target=dest_path,
                        description=f"提取 {iso_path} → {dest_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(tr("log.task_extract").format(src=iso_path, dst=dest_path))
        self._refresh_display()

    def _on_mkdir_in_iso(self, iso_path):
        task = TaskItem(TaskType.MKDIR, target=iso_path,
                        description=f"新建文件夹 {iso_path}")
        self._tasks.append(task)
        self.task_queue.add_task(task)
        self.log_viewer.append_info(tr("log.task_mkdir").format(path=iso_path))
        self._refresh_display()

    def _on_open_terminal(self, path):
        try:
            subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _on_load_iso_from_disk(self, path):
        self.drive_combo.lineEdit().setText(path)
        self._load_drive()

    def _on_burn_iso_dialog(self):
        dlg = BurnIsoDialog(self)
        dlg.execute_requested.connect(self._run_xorriso_direct)
        dlg.exec()

    def _on_toc_dialog(self):
        dlg = TocDialog(self)
        dlg.exec()

    def _on_check_media(self):
        drive = _resolve_combo_path(self.drive_combo)
        if not drive or not drive.startswith("/dev/"):
            drive = _resolve_combo_path(self.output_combo)
        if not drive or not drive.startswith("/dev/"):
            drive = "/dev/cdrom"
        args = ["-dev", drive, "-check_media",
                "time_limit=1800", "report=blocks_files"]
        display = f"xorriso -dev {drive} -check_media time_limit=1800 report=blocks_files"
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("check_media.title"))
        msg.setIcon(QMessageBox.Question)
        msg.setText(tr("check_media.text").format(drive=drive))
        msg.setDetailedText(display)
        run_btn = msg.addButton("▶ 开始检查", QMessageBox.AcceptRole)
        msg.addButton("取消", QMessageBox.RejectRole)
        if msg.exec():
            self.log_viewer.append_info("=" * 60)
            self.log_viewer.append_info(tr("log.exec_command").format(cmd=display))
            self.log_viewer.append_info("=" * 60)
            self.status_bar.showMessage(tr("status.checking"))
            QApplication.processEvents()
            self._xorriso.run(args)

    def _on_clear_tasks(self):
        reply = QMessageBox.question(self, tr("dialog.confirm_clear"), tr("dialog.confirm_clear_text"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._tasks.clear()
            self.task_queue.clear_all()
            self.log_viewer.append_info(tr("log.tasks_cleared"))
            self._refresh_display()

    def _on_task_removed(self, task):
        if task in self._tasks:
            self._tasks.remove(task)
            self._refresh_display()

    def _on_execute_clicked(self):
        if not self._build_and_confirm():
            return
        self._run_xorriso()

    def _build_and_confirm(self):
        builder = TaskBuilder()

        vid = self.volume_id_edit.text().strip()
        if vid:
            builder.set_volume_id(vid)

        input_drive = _resolve_combo_path(self.drive_combo)
        output_drive = _resolve_combo_path(self.output_combo)

        input_is_disc = input_drive.startswith("/dev/") if input_drive else False
        output_is_disc = output_drive.startswith("/dev/") if output_drive else False

        if self._is_disc_mode and input_is_disc and input_drive == output_drive:
            builder.set_same_drive(input_drive)
        elif self._is_disc_mode and input_is_disc and not output_drive:
            builder.set_same_drive(input_drive)
        elif input_drive and output_drive and input_drive == output_drive and input_is_disc:
            builder.set_same_drive(input_drive)
        elif input_drive and output_drive:
            builder.set_input_drive(input_drive)
            builder.set_output_drive(output_drive)
        elif input_drive and not output_drive:
            QMessageBox.warning(self, "错误",
                tr("error.no_output"))
            return False
        elif not input_drive and output_drive:
            builder.set_output_drive(output_drive)
        else:
            QMessageBox.warning(self, "错误",
                tr("error.no_output"))
            return False

        args = builder.build_args(self._tasks)
        display = builder.args_to_display(args)

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("confirm.title"))
        msg.setIcon(QMessageBox.Question)
        msg.setText(tr("confirm.text"))
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
        self.log_viewer.append_info(tr("log.exec_command").format(cmd=display))
        self.log_viewer.append_info("=" * 60)
        self.status_bar.showMessage(tr("status.executing"))
        QApplication.processEvents()
        self._xorriso.run(args)

    def _run_xorriso_direct(self, args, display):
        self.log_viewer.append_info("=" * 60)
        self.log_viewer.append_info(tr("log.exec_command").format(cmd=display))
        self.log_viewer.append_info("=" * 60)
        self.status_bar.showMessage(tr("status.executing"))
        QApplication.processEvents()
        self._xorriso.run(args)

    def _on_stdout(self, text):
        self.log_viewer.append_stdout(text)

    def _on_stderr(self, text):
        self.log_viewer.append_stderr(text)

    def _on_process_finished(self, exit_code):
        if exit_code == 0:
            self.log_viewer.append_success(tr("log.exec_success").format(code=exit_code))
            self.status_bar.showMessage(tr("status.success"))
            self._tasks.clear()
            self.task_queue.clear_all()
            if not self._is_disc_mode:
                QTimer.singleShot(500, self._reload_iso_after_commit)
        else:
            self.log_viewer.append_error(tr("log.exec_failed").format(code=exit_code))
            self.status_bar.showMessage(tr("status.failed").format(code=exit_code))

    def _reload_iso_after_commit(self):
        self.status_bar.showMessage(tr("status.reloading"))
        output = _resolve_combo_path(self.output_combo)
        if output:
            self._reload_worker = LoadIsoWorker(output, self)
            self._reload_worker.result.connect(self._on_reload_done)
            self._reload_worker.start()

    def _on_reload_done(self, root, error, volid):
        if not error:
            self.iso_panel.load_contents(root)
            path = self._reload_worker.drive_path
            self.status_bar.showMessage(tr("status.reloaded").format(path=path))
            if volid:
                self.volume_id_edit.setText(volid)
            self._update_media_space(path)
        else:
            self.status_bar.showMessage(tr("error.reload_failed").format(msg=error))

    def _install_focus_tracking(self):
        pass

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def _update_transfer_buttons(self):
        pass

    def _on_transfer_left(self):
        paths = self.iso_panel.get_selected_paths()
        dest = self.disk_panel.get_current_path()
        for p in paths:
            if p == "/":
                continue
            self._on_extract_from_iso(p, dest)

    def _on_transfer_right(self):
        paths = self.disk_panel.get_selected_paths()
        iso_target = self.iso_panel.get_target_directory_for_context()
        for p in paths:
            name = p.rstrip("/").rsplit("/", 1)[-1]
            iso_path = iso_target.rstrip("/") + "/" + name
            self._on_add_to_iso(p, iso_path)

    def _on_trash(self):
        for p in self.iso_panel.get_selected_paths():
            if p and p != "/":
                self._on_remove_from_iso(p)


def _split_iso_path(path):
    path = path.rstrip("/")
    if "/" not in path:
        return "/", path
    idx = path.rfind("/")
    return path[:idx] if path[:idx] else "/", path[idx + 1:]


def _find_node(root, path):
    if path == "/" or path == "":
        return root
    parts = [p for p in path.strip("/").split("/") if p]
    current = root
    for part in parts:
        found = None
        for child in current.children:
            if not child.is_placeholder and child.name == part:
                found = child
                break
        if found is None:
            return None
        current = found
    return current


def _remove_node_from_tree(root, path):
    node = _find_node(root, path)
    if node and node.parent:
        node.parent.children = [c for c in node.parent.children if c is not node]
        node.parent.sort_children()
        _add_placeholders_to_tree(root)


def _rename_node_in_tree(root, old_path, new_path):
    node = _find_node(root, old_path)
    if node:
        old_name = node.name
        new_name = new_path.rstrip("/").rsplit("/", 1)[-1]
        node.name = new_name
        node.path = new_path
        node.parent.sort_children()
        _add_placeholders_to_tree(root)


def _remove_placeholder(parent):
    parent.children = [c for c in parent.children if not c.is_placeholder]


def _add_placeholders_to_tree(node):
    if node.is_dir:
        has_real_children = any(not c.is_placeholder for c in node.children)
        node.children = [c for c in node.children if not c.is_placeholder]
        if not has_real_children:
            placeholder = FileNode(
                name="——", path="", is_dir=False,
                is_placeholder=True
            )
            node.add_child(placeholder)
        for child in node.children:
            if not child.is_placeholder:
                _add_placeholders_to_tree(child)


def _resolve_combo_path(combo):
    line_edit = combo.lineEdit()
    if line_edit:
        text = line_edit.text().strip()
    else:
        text = combo.currentText().strip()
    for i in range(combo.count()):
        if combo.itemText(i) == text:
            data = combo.itemData(i)
            if data:
                return data
            break
    return text