from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QCoreApplication, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QSpinBox,
    QGroupBox,
)

from downloader import (
    validate_url,
)
from downloader.manager import DownloadManager, DownloadRequest


QSS = """
QWidget { font-size: 12px; }
QLineEdit, QTextEdit { border: 1px solid #555; border-radius: 6px; padding: 6px; }
QTextEdit#logBox { background: #000; color: #00FF66; }
QPushButton { padding: 6px 12px; border-radius: 6px; }
QPushButton:enabled { background: #2d74da; color: white; }
QPushButton:disabled { background: #888; color: #eee; }
QProgressBar { height: 18px; border-radius: 6px; }
QProgressBar::chunk { background-color: #2d74da; border-radius: 6px; }
"""


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Motherless Single Downloader")
        self.setMinimumWidth(680)
        self._manager: Optional[DownloadManager] = None
        self._total_bytes: int = 0
        self._accept_ranges: bool = False
        self._settings: QSettings = QSettings()
        self._filename_overridden: bool = False

        self._build_ui()
        self.setStyleSheet(QSS)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # URL input
        url_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste Motherless direct HTTPS URL…")
        self.url_edit.textEdited.connect(self._on_url_edited)
        self.validate_label = QLabel("")
        self.validate_label.setStyleSheet("color: #c62828;")
        url_row.addWidget(QLabel("URL:"))
        url_row.addWidget(self.url_edit, 1)
        root.addLayout(url_row)
        root.addWidget(self.validate_label)

        # Destination row
        dest_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        self.dest_edit.setReadOnly(True)
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse_dest)
        dest_row.addWidget(QLabel("Folder:"))
        dest_row.addWidget(self.dest_edit, 1)
        dest_row.addWidget(self.browse_btn)
        root.addLayout(dest_row)
        # Default download directory (remember last used)
        last_dir_val = self._settings.value("lastDownloadDir", None)
        if isinstance(last_dir_val, str) and last_dir_val.strip():
            default_dir = last_dir_val
        else:
            default_dir = str(Path("F:/Debrid Stage"))
        self.dest_edit.setText(default_dir)

        # Filename
        fname_row = QHBoxLayout()
        self.fname_edit = QLineEdit()
        self.fname_edit.setPlaceholderText("Optional filename (auto from server if empty)")
        self.fname_edit.textEdited.connect(self._on_fname_edited)
        fname_row.addWidget(QLabel("Filename:"))
        fname_row.addWidget(self.fname_edit, 1)
        root.addLayout(fname_row)

        # Controls
        ctl_row = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.cancel_btn = QPushButton("Cancel")
        self.conn_spin = QSpinBox()
        self.conn_spin.setRange(1, 30)
        self.conn_spin.setValue(4)
        self.adapt_btn = QPushButton("Adapt OFF")
        self.adapt_btn.setCheckable(True)
        self.adapt_btn.toggled.connect(self._on_adapt_toggled)
        ctl_row.addWidget(QLabel("Connections:"))
        ctl_row.addWidget(self.conn_spin)
        ctl_row.addWidget(self.adapt_btn)
        for b in (self.pause_btn, self.resume_btn, self.cancel_btn):
            b.setEnabled(False)
        self.download_btn.clicked.connect(self._on_download)
        self.pause_btn.clicked.connect(self._on_pause)
        self.resume_btn.clicked.connect(self._on_resume)
        self.cancel_btn.clicked.connect(self._on_cancel)
        for b in (self.download_btn, self.pause_btn, self.resume_btn, self.cancel_btn):
            ctl_row.addWidget(b)
        root.addLayout(ctl_row)

        # Progress and status
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status_label = QLabel("Idle")
        self.speed_label = QLabel("0 KB/s")
        info_row = QHBoxLayout()
        info_row.addWidget(self.status_label)
        info_row.addStretch(1)
        self.conn_label = QLabel("0 conns")
        info_row.addWidget(self.conn_label)
        info_row.addSpacing(8)
        info_row.addWidget(self.speed_label)
        root.addWidget(self.progress)
        root.addLayout(info_row)

        # Default Adapt to ON after labels exist so the toggle update can refresh UI safely
        self.adapt_btn.setChecked(True)

        # Log box
        self.log = QTextEdit()
        self.log.setObjectName("logBox")
        self.log.setReadOnly(True)
        root.addWidget(self.log)

    def _browse_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Destination")
        if folder:
            self.dest_edit.setText(folder)
            self._settings.setValue("lastDownloadDir", folder)

    def _set_controls_for_running(self, running: bool) -> None:
        self.download_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running and self._accept_ranges)
        self.resume_btn.setEnabled(False)
        self.cancel_btn.setEnabled(running)

    def _on_download(self) -> None:
        url = self.url_edit.text().strip()
        url_check = validate_url(url)
        if not url_check.is_valid:
            self.validate_label.setText(url_check.message)
            return
        self.validate_label.setText("")

        dest_dir = self.dest_edit.text().strip() or str(Path.home() / "Downloads")
        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        self._settings.setValue("lastDownloadDir", str(dest_path))

        name_text = self.fname_edit.text().strip()
        explicit_filename = name_text if (self._filename_overridden and name_text) else None
        final_path = dest_path / (explicit_filename or "download.bin")

        # Remove leading '@' often used in shells/notes
        if url.startswith('@'):
            url = url[1:]
        req = DownloadRequest(url=url, dest_file=final_path, explicit_filename=explicit_filename, connections=self.conn_spin.value(), adaptive_connections=self.adapt_btn.isChecked())
        self._manager = DownloadManager(req)
        self._connect_manager()

        self._set_controls_for_running(True)
        self._append_log("Starting download…")
        adapt_suffix = " (Adapt)" if self.adapt_btn.isChecked() else ""
        self.conn_label.setText(f"{self.conn_spin.value()} conns{adapt_suffix}")
        self._manager.start()

    def _connect_manager(self) -> None:
        assert self._manager is not None
        m = self._manager
        m.progress.connect(self._on_progress)
        m.speed.connect(self._on_speed)
        m.status.connect(self._on_status)
        m.finished.connect(self._on_finished)
        if hasattr(m, "head_info"):
            m.head_info.connect(self._on_head_info)

    def _on_head_info(self, total: int, accept_ranges: bool, content_type: str, suggested: str) -> None:
        self._total_bytes = total
        self._accept_ranges = accept_ranges
        if not self.fname_edit.text().strip():
            # Populate filename suggestion
            if suggested:
                self.fname_edit.setText(suggested)
        self._append_log(f"HEAD: size={total} ranges={accept_ranges} type={content_type} filename={suggested}")
        # Update displayed active connections depending on range support
        active_conns = self.conn_spin.value() if accept_ranges else 1
        adapt_suffix = " (Adapt)" if self.adapt_btn.isChecked() else ""
        self.conn_label.setText(f"{active_conns} conns{adapt_suffix}")

    def _on_progress(self, received: int, total: int) -> None:
        if total > 0:
            pct = int(received * 100 / total)
            self.progress.setValue(pct)
        r_mb = received / 1_000_000.0
        t_mb = (total / 1_000_000.0) if total > 0 else 0.0
        self.status_label.setText(f"{r_mb:.2f}/{t_mb:.2f} MB")

    def _on_speed(self, bps: float) -> None:
        mbps = (bps * 8) / 1_000_000.0
        self.speed_label.setText(f"{mbps:.2f} Mb/s")

    def _on_status(self, msg: str) -> None:
        self._append_log(msg)

    def _on_finished(self, success: bool, message: str) -> None:
        self._append_log(message)
        self._set_controls_for_running(False)
        self.resume_btn.setEnabled(False)
        # Reset manual override state after each transfer
        self._filename_overridden = False

    def _on_pause(self) -> None:
        if self._manager:
            self._manager.pause()
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)

    def _on_resume(self) -> None:
        if self._manager:
            self._manager.resume()
            self.pause_btn.setEnabled(self._accept_ranges)
            self.resume_btn.setEnabled(False)

    def _on_cancel(self) -> None:
        if self._manager:
            self._manager.cancel()

    def _append_log(self, text: str) -> None:
        self.log.append(text)

    def _on_fname_edited(self, _text: str) -> None:
        # Mark that the user explicitly set the filename; we will honor it
        self._filename_overridden = True

    def _on_url_edited(self, _text: str) -> None:
        # When URL changes and the filename wasn't explicitly overridden, clear it
        if not self._filename_overridden:
            self.fname_edit.clear()

    def _on_adapt_toggled(self, checked: bool) -> None:
        self.adapt_btn.setText("Adapt ON" if checked else "Adapt OFF")
        # Provide a subtle visual cue when ON
        if checked:
            self.adapt_btn.setStyleSheet("background: #2e7d32; color: white;")
        else:
            self.adapt_btn.setStyleSheet("")
        # Reflect state in the connections label
        active_conns = self.conn_spin.value() if self._accept_ranges else 1
        suffix = " (Adapt)" if checked else ""
        self.conn_label.setText(f"{active_conns} conns{suffix}")


def main() -> int:
    app = QApplication(sys.argv)
    QCoreApplication.setOrganizationName("Motherless")
    QCoreApplication.setApplicationName("Motherless Single Downloader")
    w = MainWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
