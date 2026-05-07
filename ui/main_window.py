import os
from pathlib import Path

import yaml
from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from engine.detector import Detector
from engine.kpi_aggregator import KPIAggregator
from engine.pipeline import VideoPipeline
from engine.tracker import Tracker
from engine.zones import ZoneManager
from ui.kpi_panel import KPIPanel
from ui.theme_manager import ThemeManager
from ui.video_widget import EditMode, VideoWidget


class MainWindow(QMainWindow):
    def __init__(self, config_path: str, model_path: str):
        super().__init__()
        self.setWindowTitle("KPI 监控系统 — 卸货区检测")
        self.resize(1400, 850)
        self.config_path = config_path
        self.model_path = model_path

        # Engine components (created once, reused across runs)
        self.detector: Detector | None = None
        self.tracker: Tracker | None = None
        self.zone_manager: ZoneManager | None = None
        self.kpi_aggregator: KPIAggregator | None = None
        self.pipeline: VideoPipeline | None = None
        self.current_video: str | None = None
        self._elapsed_seconds: int = 0
        self._elapsed_timer: QTimer | None = None

        # Initialize engine (lightweight)
        self._init_engine()

        # UI
        self._build_ui()
        self._load_config()
        self._load_default_video()

    # engine init

    def _init_engine(self):
        """Initialize detector, tracker, zone manager, and KPI aggregator."""
        try:
            self.detector = Detector(self.model_path)
        except Exception as e:
            self.detector = None
            QMessageBox.warning(self, "模型加载失败", f"无法加载 YOLO 模型:\n{e}")

        self.tracker = Tracker()
        self.zone_manager = ZoneManager()
        self.kpi_aggregator = KPIAggregator(window_seconds=60)

    # UI construction

    def _build_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Splitter: video (left) | KPI panel (right)
        splitter = QSplitter(Qt.Horizontal)

        self.video_widget = VideoWidget()
        self.video_widget.config_changed.connect(self._on_config_changed)
        splitter.addWidget(self.video_widget)

        self.kpi_panel = KPIPanel()
        splitter.addWidget(self.kpi_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 350])
        root.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Toolbar
        self._build_toolbar()

    def _build_toolbar(self):
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        # Video controls
        tb.addWidget(QLabel(" 视频 "))

        self.action_open = QAction("打开视频", self)
        self.action_open.setShortcut(QKeySequence.Open)
        self.action_open.triggered.connect(self._open_video)
        tb.addAction(self.action_open)

        tb.addSeparator()

        self.action_play = QAction("运行", self)
        self.action_play.setShortcut(QKeySequence("Ctrl+R"))
        self.action_play.triggered.connect(self._run_pipeline)
        tb.addAction(self.action_play)

        self.action_pause = QAction("暂停", self)
        self.action_pause.setShortcut(QKeySequence("Ctrl+P"))
        self.action_pause.triggered.connect(self._pause_pipeline)
        self.action_pause.setEnabled(False)
        tb.addAction(self.action_pause)

        self.action_stop = QAction("停止", self)
        self.action_stop.setShortcut(QKeySequence("Ctrl+S"))
        self.action_stop.triggered.connect(self._stop_pipeline)
        self.action_stop.setEnabled(False)
        tb.addAction(self.action_stop)

        tb.addSeparator()

        # ROI editing
        tb.addWidget(QLabel(" ROI "))

        self.action_edit_work = QAction("编辑工作区", self)
        self.action_edit_work.setCheckable(True)
        self.action_edit_work.triggered.connect(lambda checked: self._toggle_roi_mode(
            EditMode.DRAW_WORK_ZONE if checked else EditMode.VIEW
        ))
        tb.addAction(self.action_edit_work)

        self.action_edit_idle = QAction("编辑空闲区", self)
        self.action_edit_idle.setCheckable(True)
        self.action_edit_idle.triggered.connect(lambda checked: self._toggle_roi_mode(
            EditMode.DRAW_IDLE_ZONE if checked else EditMode.VIEW
        ))
        tb.addAction(self.action_edit_idle)

        self.action_edit_line = QAction("编辑计数线", self)
        self.action_edit_line.setCheckable(True)
        self.action_edit_line.triggered.connect(lambda checked: self._toggle_roi_mode(
            EditMode.DRAW_COUNT_LINE if checked else EditMode.VIEW
        ))
        tb.addAction(self.action_edit_line)

        tb.addSeparator()

        self.action_clear_roi = QAction("清除ROI", self)
        self.action_clear_roi.triggered.connect(self._clear_current_roi)
        tb.addAction(self.action_clear_roi)

        self.action_save_config = QAction("保存配置", self)
        self.action_save_config.setShortcut(QKeySequence.Save)
        self.action_save_config.triggered.connect(self._save_config)
        tb.addAction(self.action_save_config)

        tb.addSeparator()

        self.action_toggle_roi = QAction("显示ROI", self)
        self.action_toggle_roi.setCheckable(True)
        self.action_toggle_roi.setChecked(True)
        self.action_toggle_roi.setShortcut(QKeySequence("Ctrl+H"))
        self.action_toggle_roi.triggered.connect(self._toggle_roi_visibility)
        tb.addAction(self.action_toggle_roi)

        tb.addSeparator()

        self.action_toggle_theme = QAction("切换主题", self)
        self.action_toggle_theme.setCheckable(True)
        self.action_toggle_theme.setShortcut(QKeySequence("Ctrl+T"))
        self.action_toggle_theme.triggered.connect(self._toggle_theme)
        tb.addAction(self.action_toggle_theme)

    # ROI mode toggle

    def _toggle_roi_mode(self, mode: EditMode):
        """Ensure only one ROI editing mode is active at a time."""
        self.video_widget.set_edit_mode(mode)

        # Sync button states
        self.action_edit_work.setChecked(mode == EditMode.DRAW_WORK_ZONE)
        self.action_edit_idle.setChecked(mode == EditMode.DRAW_IDLE_ZONE)
        self.action_edit_line.setChecked(mode == EditMode.DRAW_COUNT_LINE)

        if mode == EditMode.DRAW_WORK_ZONE:
            self.status_bar.showMessage("工作区绘制: 左键添加顶点 · 右键/Enter完成 · Esc取消", 0)
        elif mode == EditMode.DRAW_IDLE_ZONE:
            self.status_bar.showMessage("空闲区绘制: 左键添加顶点 · 右键/Enter完成 · Esc取消", 0)
        elif mode == EditMode.DRAW_COUNT_LINE:
            self.status_bar.showMessage("计数线绘制: 左键点击起点 → 左键点击终点 · Esc取消", 0)
        else:
            self.status_bar.showMessage("就绪", 3000)

    def _toggle_roi_visibility(self, checked: bool):
        self.video_widget.show_roi = checked
        self.action_toggle_roi.setText("隐藏ROI" if checked else "显示ROI")
        self.video_widget.update()

    def _toggle_theme(self, checked: bool):
        app = QApplication.instance()
        if checked:
            ThemeManager.apply_theme(app, ThemeManager.PIXEL)
        else:
            ThemeManager.apply_theme(app, ThemeManager.DEFAULT)
        self.action_toggle_theme.setText("切换主题")
        self.kpi_panel.apply_theme(ThemeManager.current())
        self.kpi_panel.chart.apply_theme(ThemeManager.current())
        self.video_widget.theme = ThemeManager.current()
        self.video_widget.update()

    def _clear_current_roi(self):
        """Clear the ROI corresponding to currently active button, or prompt."""
        if self.action_edit_work.isChecked():
            self.video_widget.clear_work_zone()
        elif self.action_edit_idle.isChecked():
            self.video_widget.clear_idle_zone()
        elif self.action_edit_line.isChecked():
            self.video_widget.clear_count_line()
        else:
            self.status_bar.showMessage("请先选择一个 ROI 编辑模式", 3000)

    # config

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config:
                self.video_widget.load_config(config)
                self.zone_manager = ZoneManager.from_config(config)
        except Exception as e:
            self.status_bar.showMessage(f"配置加载失败: {e}", 5000)

    def _save_config(self):
        config = self.video_widget.get_config()
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            # Sync engine
            self.zone_manager = ZoneManager.from_config({"zones": config["zones"]})
            self.status_bar.showMessage("配置已保存", 3000)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_config_changed(self):
        """Called whenever ROI vertices change (draw, drag, delete)."""
        self.status_bar.showMessage("ROI 已修改 (Ctrl+S 保存)", 3000)

    # video

    def _load_default_video(self):
        default = Path(__file__).parent.parent / "test.mp4"
        if default.exists():
            self._load_video(str(default))

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv);;所有文件 (*.*)"
        )
        if path:
            self._load_video(path)

    def _load_video(self, path: str):
        """Load a video file, show first frame, and update the window title."""
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            QMessageBox.warning(self, "打开失败", f"无法打开视频文件:\n{path}")
            return
        ret, frame = cap.read()
        cap.release()

        if ret:
            self.current_video = path
            self.video_widget.set_frame(frame)
            self.kpi_panel.set_status(f"已加载: {os.path.basename(path)}")
            self.setWindowTitle(f"KPI 监控系统 — {os.path.basename(path)}")
            self.status_bar.showMessage(
                f"已加载 {os.path.basename(path)} | 请先配置 ROI 区域，然后点击 运行",
                5000,
            )
        else:
            QMessageBox.warning(self, "读取失败", "无法从视频中读取帧。")

    # pipeline

    def _run_pipeline(self):
        """Start or restart the video processing pipeline."""
        if self.detector is None:
            QMessageBox.warning(self, "模型未加载", "YOLO 模型未加载，无法运行。")
            return

        if not self.current_video or not os.path.exists(self.current_video):
            QMessageBox.warning(self, "无视频", "请先打开一个视频文件。")
            return

        # Warn if ROI not configured
        if not self.video_widget.work_zone_points and not self.video_widget.idle_zone_points:
            reply = QMessageBox.question(
                self, "ROI 未配置",
                "尚未配置工作区/空闲区 ROI。\n\n"
                "没有 ROI 时，所有人员将被归类为\"未知\"，包裹计数线也不会工作。\n\n"
                "是否继续运行？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        # Stop previous pipeline if running
        if self.pipeline and self.pipeline.isRunning():
            self.pipeline.stop()
            self.pipeline.wait(3000)

        # Save current config to sync engine
        config = self.video_widget.get_config()
        self.zone_manager = ZoneManager.from_config({"zones": config["zones"]})
        self.kpi_aggregator.reset()

        # Create and start pipeline
        self.pipeline = VideoPipeline(
            video_path=self.current_video,
            detector=self.detector,
            tracker=self.tracker,
            zone_manager=self.zone_manager,
            kpi_aggregator=self.kpi_aggregator,
            skip_frames=2,  # process every 3rd frame
        )
        self.pipeline.frame_ready.connect(self.video_widget.set_frame)
        self.pipeline.kpi_updated.connect(self._on_kpi_update)
        self.pipeline.progress.connect(self._on_progress)
        self.pipeline.finished.connect(self._on_finished)
        self.pipeline.error.connect(self._on_error)

        self.pipeline.start()

        # UI state
        self.action_play.setEnabled(False)
        self.action_pause.setEnabled(True)
        self.action_stop.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.kpi_panel.set_status("运行中...")

        # Reset ROI edit mode
        self._toggle_roi_mode(EditMode.VIEW)

        # Elapsed timer
        self._elapsed_seconds = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._elapsed_timer.start(1000)

        self.status_bar.showMessage("管道运行中...", 0)

    def _pause_pipeline(self):
        if self.pipeline and self.pipeline.isRunning():
            if self.pipeline.is_paused:
                self.pipeline.resume()
                self.action_pause.setText("暂停")
                self.kpi_panel.set_status("运行中...")
                self.status_bar.showMessage("已恢复", 3000)
            else:
                self.pipeline.pause()
                self.action_pause.setText("继续")
                self.kpi_panel.set_status("已暂停")
                self.status_bar.showMessage("已暂停", 3000)

    def _stop_pipeline(self):
        if self.pipeline and self.pipeline.isRunning():
            self.pipeline.stop()
            self.pipeline.wait(5000)

        self._reset_ui_state()
        self.status_bar.showMessage("已停止", 3000)

    def _on_finished(self):
        self._reset_ui_state()
        self.kpi_panel.set_status("视频处理完成")
        self.status_bar.showMessage("视频处理完成", 5000)

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "处理错误", msg)
        self._reset_ui_state()

    def _on_progress(self, pct: int):
        self.progress_bar.setValue(pct)

    def _on_kpi_update(self, data: dict):
        self.kpi_panel.update_kpi(data)
        # Update chart periodically from history
        self.kpi_panel.chart.update_from_history(self.kpi_aggregator.get_window_history())

    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        m, s = divmod(self._elapsed_seconds, 60)
        self.kpi_panel.set_time(f"运行时长: {m:02d}:{s:02d}")

    def _reset_ui_state(self):
        if self._elapsed_timer:
            self._elapsed_timer.stop()
            self._elapsed_timer = None

        self.action_play.setEnabled(True)
        self.action_pause.setEnabled(False)
        self.action_pause.setText("暂停")
        self.action_stop.setEnabled(False)
        self.progress_bar.setVisible(False)

    # close

    def closeEvent(self, event):
        if self.pipeline and self.pipeline.isRunning():
            self.pipeline.stop()
            self.pipeline.wait(3000)
        super().closeEvent(event)
