#!/usr/bin/env python3
"""
FileBridge – v0.1.0 “Bombardino Crocodilo”
Cross‑platform file transfer GUI with Google Drive support.
"""
import sys
import os
import shutil
import subprocess
import html
import pickle
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
import qdarkstyle

# Google Drive API imports
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Version info
__version__ = "0.1.0"
__codename__ = "Bombardino Crocodilo"

# OAuth2 scope: per‑file access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def file_exists(path: str) -> bool:
    """Helper for tests."""
    return os.path.isfile(path)


class Worker(QtCore.QThread):
    """
    Background worker for file transfers.
    Emits:
      - status(str message, bool is_error)
      - progress(int percent)
    """
    status = QtCore.pyqtSignal(str, bool)
    progress = QtCore.pyqtSignal(int)

    def __init__(self, src, mode, partition=None):
        super().__init__()
        self.src = src
        self.mode = mode
        self.partition = partition
        self.mount_point = "/mnt/shared"
        self.local_dest = os.path.expanduser("~/Documents/Transfers")
        self.win_subpath = "Users/Yashp/Downloads"
        # Paths for Google credentials/token
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        self.cred_path = project_root / "credentials.json"
        self.token_path = project_root / "token.pickle"

    def run(self):
        basename = os.path.basename(self.src)

        # 1) Validate source file
        if not os.path.isfile(self.src):
            self.status.emit(f"Error: source not found: {self.src}", True)
            return
        self.status.emit(f"✔ Source validated: {self.src}", False)

        # 2) Dispatch by mode
        if self.mode == "local":
            self._transfer_local(basename)

        elif self.mode == "windows":
            self._transfer_windows(basename)

        elif self.mode == "gdrive":
            self._transfer_gdrive(basename)

        else:
            self.status.emit(f"Error: unknown mode '{self.mode}'", True)

    def _transfer_local(self, basename):
        """Copy to local ~/Documents/Transfers."""
        try:
            os.makedirs(self.local_dest, exist_ok=True)
            dest = os.path.join(self.local_dest, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                return
            self.copy_with_progress(self.src, dest)
        except Exception as e:
            self.status.emit(f"Local transfer failed: {e}", True)

    def _transfer_windows(self, basename):
        """Mount Windows partition, copy, then unmount."""
        # Prepare mount point
        try:
            if not os.path.isdir(self.mount_point):
                os.makedirs(self.mount_point, exist_ok=True)
                self.status.emit(f"Created mount point: {self.mount_point}", False)
        except PermissionError:
            self.status.emit(
                f"Permission denied creating '{self.mount_point}'.\n"
                f"Run: sudo mkdir -p {self.mount_point} && sudo chown $USER:$USER {self.mount_point}",
                True
            )
            return

        part = self.partition or "/dev/nvme0n1p3"
        try:
            subprocess.check_call(["sudo", "mount", "-o", "rw", part, self.mount_point])
            self.status.emit(f"✔ Mounted {part}", False)
        except subprocess.CalledProcessError as e:
            self.status.emit(f"Mount failed: {e}", True)
            return

        try:
            dest_folder = os.path.join(self.mount_point, self.win_subpath)
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                return
            self.copy_with_progress(self.src, dest)
        except Exception as e:
            self.status.emit(f"Windows transfer failed: {e}", True)
        finally:
            try:
                subprocess.check_call(["sudo", "umount", self.mount_point])
                self.status.emit(f"✔ Unmounted {self.mount_point}", False)
            except subprocess.CalledProcessError as e:
                self.status.emit(f"Unmount failed: {e}", True)

    def _transfer_gdrive(self, basename):
        """Authenticate, then upload to Google Drive with progress."""
        creds = None

        # 1) Load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token_file:
                    creds = pickle.load(token_file)
            except Exception as e:
                self.status.emit(f"Warning: failed to load token: {e}", False)

        # 2) Refresh or request new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.status.emit("Refreshed Google credentials", False)
                except Exception as e:
                    self.status.emit(f"Error refreshing credentials: {e}", True)
                    return
            else:
                if not self.cred_path.exists():
                    self.status.emit(
                        f"Error: credentials.json not found at {self.cred_path}", True
                    )
                    return
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.cred_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    self.status.emit("Google authentication successful", False)
                except Exception as e:
                    self.status.emit(f"Authentication failed: {e}", True)
                    return
            # Save new token
            try:
                with open(self.token_path, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                    self.status.emit(f"Saved token to {self.token_path}", False)
            except Exception as e:
                self.status.emit(f"Warning: could not save token: {e}", False)

        # 3) Build Drive service
        try:
            service = build('drive', 'v3', credentials=creds)
            self.status.emit("Google Drive service initialized", False)
        except Exception as e:
            self.status.emit(f"Failed to initialize Drive service: {e}", True)
            return

        # 4) Prepare upload
        try:
            file_size = os.path.getsize(self.src)
            media = MediaFileUpload(self.src, resumable=True)
            file_metadata = {'name': basename}
            request = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
        except Exception as e:
            self.status.emit(f"Error preparing upload: {e}", True)
            return

        # 5) Perform resumable upload with progress
        try:
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    self.progress.emit(pct)
                    self.status.emit(f"Upload progress: {pct}%", False)
            file_id = response.get('id')
            self.status.emit(f"✔ Uploaded to Google Drive (ID: {file_id})", False)
            self.progress.emit(100)
        except Exception as e:
            self.status.emit(f"Error during upload: {e}", True)

    def copy_with_progress(self, src, dest):
        """Copy file in chunks, emitting progress."""
        total = os.path.getsize(src)
        copied = 0
        bufsize = 4 * 1024 * 1024  # 4 MB chunks

        try:
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
        except Exception as e:
            self.status.emit(f"Error copying file: {e}", True)


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileBridge")
        self.resize(900, 500)
        self.build_ui()
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
        self.log.setStyleSheet("background: black; font-family: monospace;")
        right.addWidget(self.log)

        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File")
        if path:
            self.file_edit.setText(path)

    def toggle_override(self, state):
        if state == QtCore.Qt.Checked:
            self.combo.clear()
            try:
                out = subprocess.check_output(
                    ["lsblk", "-lnp", "-o", "NAME,TYPE"],
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in out.splitlines():
                    name, typ = line.split()
                    if typ == "part":
                        self.combo.addItem(name)
            except Exception as e:
                self.append_log(f"Failed to list partitions: {e}", True)
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

        # Disable buttons
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
