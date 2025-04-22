"""
Fedora → Windows/Cloud Transfer

4. Google Drive API setup:
   a. Go to https://console.developers.google.com/
   b. Create a new project (or select existing).
   c. Enable the Google Drive API for the project.
   d. Under "Credentials", create an OAuth 2.0 Client ID (application type: Desktop).
   e. Download the JSON (rename to credentials.json) and place it alongside this script.

Running the application:
   python FedoraFilesToWindows.py

Notes:
- On first Google Drive upload, a browser window will open for OAuth consent. A token.pickle file is created for subsequent runs.
- Ensure '/mnt/shared' is owned by your user for Windows transfers:
      sudo mkdir -p /mnt/shared
      sudo chown $USER:$USER /mnt/shared
"""

import sys
import os
import shutil
import subprocess
import html
import pickle

from PyQt5 import QtCore, QtWidgets, QtGui
import qdarkstyle  # pip install qdarkstyle

# Google Drive API imports
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these SCOPES, delete token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class Worker(QtCore.QThread):
    """
    Background thread to handle file transfer with progress updates.
    Modes:
      - 'local': direct copy to Transfers folder.
      - 'windows': mount -> chunked copy -> unmount.
      - 'gdrive': upload to Google Drive via API.
    Signals:
      status(str, bool): log messages (text, is_error).
      progress(int): progress percentage (0-100).
    """
    status = QtCore.pyqtSignal(str, bool)
    progress = QtCore.pyqtSignal(int)

    def __init__(self, src_path, mode, partition=None):
        super().__init__()
        self.src = src_path
        self.mode = mode
        self.partition = partition
        self.mount_point = "/mnt/shared"
        self.local_dest = "/home/yoshiunix/Documents/Transfers"
        self.win_subpath = "Users/Yashp/Downloads"

    @staticmethod
    def get_gdrive_service():
        """
        Authenticate and return a Google Drive service instance.
        Expects 'credentials.json' in working directory.
        """
        from google.auth.transport.requests import Request
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('drive', 'v3', credentials=creds)

    def copy_with_progress(self, src, dst):
        """Copy file in chunks, emitting progress signals."""
        total = os.path.getsize(src)
        copied = 0
        chunk_size = 1024 * 1024  # 1 MB
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            while True:
                buf = fsrc.read(chunk_size)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                percent = int(copied * 100 / total)
                self.progress.emit(percent)
        self.progress.emit(100)

    def run(self):
        # Validate source exists
        if not os.path.isfile(self.src):
            self.status.emit(f"Source file not found: {self.src}", True)
            return
        self.status.emit(f"✔ Source validated: {self.src}", False)
        self.progress.emit(0)

        # LOCAL copy
        if self.mode == 'local':
            try:
                os.makedirs(self.local_dest, exist_ok=True)
                self.status.emit(f"Using local folder: {self.local_dest}", False)
                dest = os.path.join(self.local_dest, os.path.basename(self.src))
                if os.path.exists(dest):
                    self.status.emit(f"Error: File already exists: {dest}", True)
                    return
                self.status.emit("Starting local copy...", False)
                self.copy_with_progress(self.src, dest)
                self.status.emit(f"✔ Copied to {dest}", False)
            except Exception as e:
                self.status.emit(f"Error copying locally: {e}", True)

        # WINDOWS mount + copy
        elif self.mode == 'windows':
            try:
                if not os.path.isdir(self.mount_point):
                    os.makedirs(self.mount_point, exist_ok=True)
                    self.status.emit(f"Created mount point: {self.mount_point}", False)
            except PermissionError:
                self.status.emit(
                    f"Permission denied creating mount point.\n"
                    f"Run: sudo mkdir -p {self.mount_point} && sudo chown $USER:$USER {self.mount_point}", True)
                return
            part = self.partition or '/dev/nvme0n1p3'
            self.status.emit(f"Mounting {part}...", False)
            try:
                subprocess.check_call(['sudo','mount','-o','rw',part,self.mount_point])
                self.status.emit(f"✔ Mounted {part}", False)
            except subprocess.CalledProcessError as e:
                self.status.emit(f"Mount failed: {e}", True)
                return
            dest_folder = os.path.join(self.mount_point, self.win_subpath)
            try:
                os.makedirs(dest_folder, exist_ok=True)
                self.status.emit(f"Using Windows folder: {dest_folder}", False)
                dest = os.path.join(dest_folder, os.path.basename(self.src))
                if os.path.exists(dest):
                    self.status.emit(f"Error: File exists: {dest}", True)
                else:
                    self.status.emit("Starting Windows copy...", False)
                    self.copy_with_progress(self.src, dest)
                    self.status.emit(f"✔ Copied to {dest}", False)
            except Exception as e:
                self.status.emit(f"Error copying to Windows: {e}", True)
            try:
                subprocess.check_call(['sudo','umount',self.mount_point])
                self.status.emit(f"✔ Unmounted {self.mount_point}", False)
            except subprocess.CalledProcessError as e:
                self.status.emit(f"Unmount failed: {e}", True)

        # GOOGLE DRIVE upload
        elif self.mode == 'gdrive':
            try:
                service = self.get_gdrive_service()
                self.status.emit("Authenticated with Google Drive", False)
                file_metadata = {'name': os.path.basename(self.src)}
                media = MediaFileUpload(self.src, chunksize=1024*1024, resumable=True)
                request = service.files().create(body=file_metadata,
                                                 media_body=media,
                                                 fields='id')
                self.status.emit("Starting Google Drive upload...", False)
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        percent = int(status.progress() * 100)
                        self.progress.emit(percent)
                        self.status.emit(f"Upload {percent}%", False)
                self.progress.emit(100)
                file_id = response.get('id')
                self.status.emit(f"✔ Uploaded to Drive, file ID: {file_id}", False)
            except Exception as e:
                self.status.emit(f"Google Drive upload error: {e}", True)

        else:
            self.status.emit(f"Unknown mode: {self.mode}", True)

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fedora → Windows/Cloud Transfer")
        self.resize(900, 550)
        layout = QtWidgets.QHBoxLayout(self)

        # LEFT: controls
        left = QtWidgets.QVBoxLayout()
        layout.addLayout(left,1)
        left.addWidget(QtWidgets.QLabel("Select file to transfer:"))
        row = QtWidgets.QHBoxLayout()
        self.file_edit = QtWidgets.QLineEdit()
        btn_browse = QtWidgets.QPushButton("Browse…")
        btn_browse.clicked.connect(self.browse_file)
        row.addWidget(self.file_edit)
        row.addWidget(btn_browse)
        left.addLayout(row)

        self.chk_override = QtWidgets.QCheckBox("Override partition selection")
        self.chk_override.stateChanged.connect(self.toggle_override)
        left.addWidget(self.chk_override)
        self.combo_part = QtWidgets.QComboBox(); self.combo_part.setVisible(False)
        left.addWidget(self.combo_part)

        left.addStretch()
        for label, mode in [
            ("Transfer to Local Transfers", 'local'),
            ("Transfer to Windows Downloads", 'windows'),
            ("Transfer to Google Drive", 'gdrive'),
        ]:
            btn = QtWidgets.QPushButton(label)
            btn.setMinimumHeight(60)
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Fixed)
            btn.clicked.connect(lambda _,m=mode: self.start_transfer(m))
            left.addWidget(btn)
        left.addStretch()

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar();
        self.progress_bar.setRange(0,100); self.progress_bar.setTextVisible(False)
        left.addWidget(self.progress_bar)

        # RIGHT: log
        right = QtWidgets.QVBoxLayout()
        layout.addLayout(right,2)
        right.addWidget(QtWidgets.QLabel("Log Output:"))
        self.log_view = QtWidgets.QTextEdit(); self.log_view.setReadOnly(True)
        font = QtGui.QFont("Courier",10); self.log_view.setFont(font)
        self.log_view.setStyleSheet("background-color:black;color:white;")
        right.addWidget(self.log_view)

        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def browse_file(self):
        path,_ = QtWidgets.QFileDialog.getOpenFileName(self,"Select File")
        if path: self.file_edit.setText(path)

    def toggle_override(self,state):
        if state==QtCore.Qt.Checked:
            parts = self.get_partitions()
            if parts: self.combo_part.clear(); self.combo_part.addItems(parts)
            else: self.append_log("No partitions found.",True)
            self.combo_part.setVisible(True)
        else:
            self.combo_part.setVisible(False)

    def get_partitions(self):
        try:
            out = subprocess.check_output(["lsblk","-lnp","-o","NAME,TYPE"],stderr=subprocess.DEVNULL).decode()
            return [l.split()[0] for l in out.splitlines() if l.split()[1]=='part']
        except Exception as e:
            self.append_log(f"Partition list error: {e}",True)
            return []

    def start_transfer(self,mode):
        src = self.file_edit.text().strip()
        if not src:
            self.append_log("Please select a file.",True)
            return
        part = None
        if mode=='windows' and self.chk_override.isChecked():
            part=self.combo_part.currentText()
            if not part: self.append_log("No partition selected.",True); return

        # Disable UI
        for w in self.findChildren(QtWidgets.QPushButton): w.setEnabled(False)
        self.log_view.clear(); self.progress_bar.setValue(0)

        self.worker = Worker(src,mode,partition=part)
        self.worker.status.connect(self.append_log)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_done)
        self.worker.start()

    def on_done(self):
        for w in self.findChildren(QtWidgets.QPushButton): w.setEnabled(True)

    def append_log(self,msg,error=False):
        safe=html.escape(msg); color='red' if error else 'lightgreen'
        self.log_view.append(f'<span style="color:{color}">{safe}</span>')


def main():
    app=QtWidgets.QApplication(sys.argv)
    wnd=MainWindow(); wnd.show()
    sys.exit(app.exec_())

if __name__=='__main__': main()
