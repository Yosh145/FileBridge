#!/usr/bin/env python3
"""
FileBridge – v0.1.2 “Bombardino Crocodilo”
Cross‑platform file transfer GUI.
"""
import sys
import os
import shutil
import subprocess
import html

from PyQt5 import QtCore, QtWidgets
import qdarkstyle

# Version info
__version__ = "0.1.2"
__codename__ = "Bombardino Crocodilo"

def file_exists(path: str) -> bool:
    """Helper for tests."""
    return os.path.isfile(path)


class Worker(QtCore.QThread):
    """Background worker for file transfers."""
    status = QtCore.pyqtSignal(str, bool)   # (message, is_error)
    progress = QtCore.pyqtSignal(int)       # percent complete

    def __init__(self, src, mode, partition=None):
        super().__init__()
        self.src = src
        self.mode = mode
        self.partition = partition
        self.mount_point = "/mnt/shared"
        self.local_dest = os.path.expanduser("~/Documents/Transfers")
        self.win_subpath = "Users/Yashp/Downloads"

    def run(self):
        basename = os.path.basename(self.src)

        # 1) Validate source
        if not os.path.isfile(self.src):
            self.status.emit(f"Error: source not found: {self.src}", True)
            return
        self.status.emit(f"✔ Source validated: {self.src}", False)

        # 2) Dispatch by mode
        if self.mode == "local":
            os.makedirs(self.local_dest, exist_ok=True)
            dest = os.path.join(self.local_dest, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                return
            self.copy_with_progress(self.src, dest)

        elif self.mode == "windows":
            # Ensure mount point exists
            try:
                if not os.path.isdir(self.mount_point):
                    os.makedirs(self.mount_point, exist_ok=True)
                    self.status.emit(f"Created mount point: {self.mount_point}", False)
            except PermissionError:
                self.status.emit(
                    f"Permission denied creating '{self.mount_point}'.\n"
                    f"Please: sudo mkdir -p {self.mount_point} && sudo chown $USER:$USER {self.mount_point}",
                    True
                )
                return

            part = self.partition or "/dev/nvme0n1p3"
            # Mount
            try:
                subprocess.check_call(["sudo", "mount", "-o", "rw", part, self.mount_point])
                self.status.emit(f"✔ Mounted {part}", False)
            except subprocess.CalledProcessError as e:
                self.status.emit(f"Mount failed: {e}", True)
                return

            # Copy
            dest_folder = os.path.join(self.mount_point, self.win_subpath)
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                subprocess.call(["sudo", "umount", self.mount_point])
                return
            self.copy_with_progress(self.src, dest)

            # Unmount
            try:
                subprocess.check_call(["sudo", "umount", self.mount_point])
                self.status.emit(f"✔ Unmounted {self.mount_point}", False)
            except subprocess.CalledProcessError as e:
                self.status.emit(f"Unmount failed: {e}", True)

        else:
            self.status.emit(f"Error: unknown mode '{self.mode}'", True)

    def copy_with_progress(self, src, dest):
        """Copy file in chunks, emitting progress."""
        total = os.path.getsize(src)
        copied = 0
        bufsize = 4 * 1024 * 1024

        with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
            while True:
                buf = fsrc.read(bufsize)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                pct = int(copied / total * 100)
                self.progress.emit(pct)

        self.status.emit(f"✔ Copied to {dest}", False)
        self.progress.emit(100)


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileBridge")
        self.resize(900, 500)

        self.build_ui()

        # Show version banner on startup
        banner = f"============== FileBridge {__version__} - {__codename__} =============="
        self.append_log(banner, False)

    def build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        left = QtWidgets.QVBoxLayout()
        right = QtWidgets.QVBoxLayout()
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)

        # File selector
        left.addWidget(QtWidgets.QLabel("File to transfer:"))
        row = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        btn_browse = QtWidgets.QPushButton("Browse…")
        btn_browse.clicked.connect(self.browse)
        row.addWidget(self.file_edit)
        row.addWidget(btn_browse)
        left.addLayout(row)

        # Override partition
        self.chk_override = QtWidgets.QCheckBox("Override partition")
        self.chk_override.stateChanged.connect(self.toggle_override)
        left.addWidget(self.chk_override)
        self.combo = QtWidgets.QComboBox()
        self.combo.setVisible(False)
        left.addWidget(self.combo)

        # Top spacer
        spacer_top = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        left.addItem(spacer_top)

        # Action buttons
        for label, mode in [
            ("Local Transfers", "local"),
            ("Windows Downloads", "windows"),
            ("Google Drive", "gdrive")
        ]:
            btn = QtWidgets.QPushButton(f"→ {label} ←")
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda _, m=mode: self.start(m))
            left.addWidget(btn)

        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(False)
        left.addWidget(self.progress)

        # Bottom spacer
        spacer_bottom = QtWidgets.QSpacerItem(
            20, 40,
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        left.addItem(spacer_bottom)

        # Log terminal on right
        right.addWidget(QtWidgets.QLabel("Log:"))
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        # Black background, monospace font
        self.log.setStyleSheet("background: black; font-family: monospace;")
        right.addWidget(self.log)

        # Apply dark theme
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")
        if path:
            self.file_edit.setText(path)

    def toggle_override(self, state):
        if state == QtCore.Qt.Checked:
            self.combo.clear()
            out = subprocess.check_output(
                ["lsblk", "-lnp", "-o", "NAME,TYPE"],
                stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                name, typ = line.split()
                if typ == "part":
                    self.combo.addItem(name)
            self.combo.setVisible(True)
        else:
            self.combo.setVisible(False)

    def start(self, mode):
        src = self.file_edit.text().strip()
        if not src:
            self.append_log("Error: no file selected.", True)
            return

        part = None
        if mode == "windows" and self.chk_override.isChecked():
            part = self.combo.currentText()
            if not part:
                self.append_log("Error: no partition chosen.", True)
                return

        # Disable all buttons during operation
        for btn in self.findChildren(QtWidgets.QPushButton):
            btn.setEnabled(False)

        self.log.clear()
        self.progress.setValue(0)

        self.worker = Worker(src, mode, partition=part)
        self.worker.status.connect(self.append_log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.enable_ui)
        self.worker.start()

    def enable_ui(self):
        for btn in self.findChildren(QtWidgets.QPushButton):
            btn.setEnabled(True)

    def append_log(self, message, is_error):
        color = "red" if is_error else "lightgreen"
        safe = html.escape(message)
        self.log.append(f'<span style="color:{color}">{safe}</span>')


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
