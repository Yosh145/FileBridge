#!/usr/bin/env python3
"""
FileBridge – v0.1.0 “Bombardino Crocodilo”
Cross‑platform file transfer GUI.
"""
import sys, os, shutil, subprocess, html
from PyQt5 import QtCore, QtWidgets
import qdarkstyle

# Version info
__version__ = "0.1.0"
__codename__ = "Bombardino Crocodilo"

def file_exists(path: str) -> bool:
    """Helper for tests."""
    return os.path.isfile(path)

class Worker(QtCore.QThread):
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

    def run(self):
        # Banner already shown in GUI init
        if not os.path.isfile(self.src):
            self.status.emit(f"Source not found: {self.src}", True)
            return
        self.status.emit(f"✔ Source: {self.src}", False)

        basename = os.path.basename(self.src)
        if self.mode == "local":
            os.makedirs(self.local_dest, exist_ok=True)
            dest = os.path.join(self.local_dest, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                return
            self.copy_with_progress(self.src, dest)

        else:  # windows
            os.makedirs(self.mount_point, exist_ok=True)
            part = self.partition or "/dev/nvme0n1p3"
            try:
                subprocess.check_call(["sudo","mount","-o","rw",part,self.mount_point])
                self.status.emit(f"✔ Mounted {part}", False)
            except Exception as e:
                self.status.emit(f"Mount failed: {e}", True)
                return

            dest_folder = os.path.join(self.mount_point, self.win_subpath)
            os.makedirs(dest_folder, exist_ok=True)
            dest = os.path.join(dest_folder, basename)
            if os.path.exists(dest):
                self.status.emit(f"Error: {dest} already exists.", True)
                subprocess.call(["sudo","umount",self.mount_point])
                return
            self.copy_with_progress(self.src, dest)
            subprocess.call(["sudo","umount",self.mount_point])
            self.status.emit(f"✔ Unmounted {self.mount_point}", False)

    def copy_with_progress(self, src, dest):
        """Copy file in chunks, emitting progress."""
        total = os.path.getsize(src)
        copied = 0
        bufsize = 4*1024*1024
        with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
            while True:
                buf = fsrc.read(bufsize)
                if not buf: break
                fdst.write(buf)
                copied += len(buf)
                pct = int(copied/total * 100)
                self.progress.emit(pct)
        self.status.emit(f"✔ Copied to {dest}", False)
        self.progress.emit(100)

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileBridge")
        self.resize(900, 500)
        self.build_ui()
        # Show version banner
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
        qb = QtWidgets.QPushButton("Browse…")
        qb.clicked.connect(self.browse)
        row.addWidget(self.file_edit); row.addWidget(qb)
        left.addLayout(row)

        # Override partition
        self.chk = QtWidgets.QCheckBox("Override partition")
        self.chk.stateChanged.connect(self.toggle_override)
        left.addWidget(self.chk)
        self.combo = QtWidgets.QComboBox(); self.combo.setVisible(False)
        left.addWidget(self.combo)

        # Action buttons
        spacer = QtWidgets.QSpacerItem(20,40,QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Expanding)
        left.addItem(spacer)
        for label,mode in [("Local Transfers","local"),("Windows Downloads","windows"),("Google Drive","gdrive")]:
            btn = QtWidgets.QPushButton(f"→ {label} ←")
            btn.setMinimumHeight(60)
            btn.clicked.connect(lambda _,m=mode: self.start(m))
            left.addWidget(btn)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(False)
        left.addWidget(self.progress)
        left.addItem(spacer.clone())

        # Log terminal
        right.addWidget(QtWidgets.QLabel("Log:"))
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        # monospace + black bg
        self.log.setStyleSheet("background:black; font-family:monospace;")
        right.addWidget(self.log)

        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def browse(self):
        p,_ = QtWidgets.QFileDialog.getOpenFileName(self,"Select File")
        if p: self.file_edit.setText(p)

    def toggle_override(self, st):
        if st == QtCore.Qt.Checked:
            self.combo.clear()
            out = subprocess.check_output(["lsblk","-lnp","-o","NAME,TYPE"]).decode()
            for l in out.splitlines():
                n,t = l.split()
                if t=="part": self.combo.addItem(n)
            self.combo.setVisible(True)
        else:
            self.combo.setVisible(False)

    def start(self, mode):
        src = self.file_edit.text().strip()
        if not src:
            self.append_log("Error: no file selected.", True); return
        part = None
        if mode=="windows" and self.chk.isChecked():
            part = self.combo.currentText()
            if not part:
                self.append_log("Error: no partition chosen.", True); return

        # disable UI
        for w in self.findChildren(QtWidgets.QPushButton): w.setEnabled(False)
        self.log.clear()
        self.progress.setValue(0)

        self.worker = Worker(src, mode, partition=part)
        self.worker.status.connect(self.append_log)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.enable_ui)
        self.worker.start()

    def enable_ui(self):
        for w in self.findChildren(QtWidgets.QPushButton): w.setEnabled(True)

    def append_log(self, msg, err):
        c = "red" if err else "lightgreen"
        self.log.append(f'<span style="color:{c}">{html.escape(msg)}</span>')

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
