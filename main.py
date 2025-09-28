import os
import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget,
    QStackedWidget, QLineEdit, QInputDialog
)

from core.const import stylesheet


class OnboardingPage(QWidget):
    def __init__(self, switch_to_auth, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stack = QStackedWidget()
        self.pages = []

        # Define onboarding content (title, subtitle)
        data = [
            ("Welcome to PushBox 🚀", "Your secure GitHub-powered cloud backup tool."),
            ("Why GitHub?",
             "GitHub gives you free, fast, and reliable cloud storage using repositories, and we can use that storage as our personal storage backup."),
            ("How it Works ⚙️", "PushBox creates repos, pushes your folders, and restores when needed."),
            ("You're Ready!", "Let's get started with secure backups.")
        ]

        for i, (title, subtitle) in enumerate(data):
            page = QWidget()
            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label_title = QLabel(title)
            label_title.setFont(QFont("Montserrat", 28, QFont.Weight.Bold))
            label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label_sub = QLabel(subtitle)
            label_sub.setFont(QFont("Arial", 12))
            label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_sub.setWordWrap(True)

            btn = QPushButton("Next" if i < len(data) - 1 else "Get Started")
            btn.setFixedWidth(150)

            # capture i in lambda properly
            def make_handler(idx):
                return lambda: self.next_page(idx, switch_to_auth)

            btn.clicked.connect(make_handler(i))

            layout.addStretch()
            layout.addWidget(label_title)
            layout.addSpacing(10)
            layout.addWidget(label_sub)
            layout.addStretch()
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

            page.setLayout(layout)
            self.pages.append(page)
            self.stack.addWidget(page)

        vbox = QVBoxLayout()
        vbox.addWidget(self.stack)
        self.setLayout(vbox)

    def next_page(self, index, switch_to_auth):
        # if not last page, show next
        if index < len(self.pages) - 1:
            self.stack.setCurrentIndex(index + 1)
        else:
            # mark onboarding done in config and save
            self.config_manager.data["onboarding_done"] = True
            self.config_manager.save_config()
            switch_to_auth()


# ---------- Auth ----------
class AuthPage(QWidget):
    def __init__(self, switch_to_dashboard, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("PushBox")
        title.setFont(QFont("Montserrat", 48, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Secure GitHub Backup")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("GitHub Username")

        self.token = QLineEdit()
        self.token.setPlaceholderText("Personal Access Token")
        self.token.setEchoMode(QLineEdit.EchoMode.Password)

        # Load saved creds if available
        cfg = self.config_manager.load_config()
        self.username.setText(cfg.get("username", ""))
        self.token.setText(cfg.get("token", ""))

        self.login_btn = QPushButton("Save & Continue")
        self.login_btn.clicked.connect(lambda: self.save_and_continue(switch_to_dashboard))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addWidget(self.username)
        layout.addWidget(self.token)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def save_and_continue(self, switch_to_dashboard):
        data = {
            "username": self.username.text(),
            "token": self.token.text(),
            # preserve onboarding flag if previously set
            "onboarding_done": self.config_manager.data.get("onboarding_done", False)
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()


# ---------- Backup ----------
class BackupPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label = QLabel("Select a folder to backup")
        self.select_btn = QPushButton("Choose Folder to Backup")
        self.backup_btn = QPushButton("Backup Now")
        self.backup_btn.setEnabled(False)  # enabled after folder chosen

        self.selected_folder_label = QLabel("No folder selected")
        self.selected_folder_label.setWordWrap(True)

        layout.addWidget(self.label)
        layout.addWidget(self.selected_folder_label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.backup_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.setLayout(layout)

        # internal state
        self.current_folder = None
        self.current_repo_name = None

        # hooks
        self.select_btn.clicked.connect(self.choose_folder_dialog)
        self.backup_btn.clicked.connect(self.start_backup)

    def choose_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to backup")
        if not folder:
            return
        self.current_folder = Path(folder)
        size = self.folder_size_bytes(self.current_folder)
        if size > 1_000_000_000:
            QMessageBox.warning(self, "Folder too large",
                                "Selected folder exceeds 1GB limit. Please choose a smaller folder.")
            self.current_folder = None
            self.selected_folder_label.setText("No folder selected")
            self.backup_btn.setEnabled(False)
            return

        # propose repo name derived from folder name and timestamp
        base_name = self.current_folder.name
        repo_name = f"backup-{base_name}"
        self.current_repo_name = repo_name
        self.selected_folder_label.setText(f"Selected: {self.current_folder}\nRepo name: {repo_name}\nSize: {self.human_readable_size(size)}")
        self.backup_btn.setEnabled(True)

    def start_backup(self):
        if not self.current_folder or not self.current_repo_name:
            QMessageBox.information(self, "No folder", "Choose a folder before backup.")
            return

        # TODO: create repo on GitHub using token and username from config_manager
        # TODO: initialize local temporary repo or use git to add/commit files, then push to created repo
        # For now simulate upload progress by iterating files and updating progress bar

        total_size = self.folder_size_bytes(self.current_folder)
        if total_size == 0:
            QMessageBox.information(self, "Empty", "Selected folder is empty.")
            return

        uploaded = 0
        self.progress.setValue(0)
        # Walk files in sorted order to make deterministic progress
        all_files = []
        for dp, dn, filenames in os.walk(self.current_folder):
            for f in filenames:
                all_files.append(Path(dp) / f)
        all_files.sort()

        # simulate uploading each file (replace with actual push logic)
        for p in all_files:
            try:
                s = p.stat().st_size
            except Exception:
                s = 0
            uploaded += s
            perc = int((uploaded / total_size) * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()  # keep UI responsive

        self.progress.setValue(100)
        QMessageBox.information(self, "Backup complete", f"Folder backed up as repo: {self.current_repo_name}")

        # Add to repo list stored in config (local cache). Real app should verify with GitHub
        repos = self.config_manager.data.get("repos", [])
        if self.current_repo_name not in repos:
            repos.append(self.current_repo_name)
            self.config_manager.data["repos"] = repos
            self.config_manager.save_config()


    @staticmethod
    def folder_size_bytes(path: Path) -> int:
        total = 0
        for dp, dn, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except Exception:
                    pass
        return total

    @staticmethod
    def human_readable_size(n: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if n < 1024:
                return f"{n:.2f}{unit}"
            n /= 1024
        return f"{n:.2f}PB"


# ---------- Restore ----------
class RestorePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("List of backup repos will show here"))
        self.setLayout(layout)


# ---------- Settings ----------
class SettingsPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings (theme, token storage, etc.)"))
        self.setLayout(layout)


# ---------- Dashboard ----------
from core.config import ConfigManager

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")

import requests
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QMessageBox, QFileDialog, QProgressBar, QApplication
)

class DashboardPage(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        layout = QHBoxLayout(self)

        # Left: Virtual Folders
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Your Virtual Folders"))

        self.folder_list = QListWidget()
        left_v.addWidget(self.folder_list)

        self.new_folder_btn = QPushButton("+ New Virtual Folder")
        left_v.addWidget(self.new_folder_btn)
        self.new_folder_btn.clicked.connect(self.create_virtual_folder)
        self.add_file_btn = QPushButton("+ Add File(s)")
        self.upload_btn = QPushButton("Push Selected Folder to GitHub")
        self.upload_btn.setEnabled(False)
        self.add_file_btn.setEnabled(False)

        left_v.addWidget(self.add_file_btn)
        left_v.addWidget(self.upload_btn)

        # Right: Files inside selected folder
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel("Files in Selected Folder"))

        self.file_list = QListWidget()
        right_v.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right_v.addWidget(self.progress)

        layout.addLayout(left_v, stretch=1)
        layout.addLayout(right_v, stretch=2)
        self.setLayout(layout)

        # Internal state
        self.virtual_folders = {}  # folder_name -> list of Path objects
        self.current_folder = None

        # Hooks
        self.folder_list.currentTextChanged.connect(self.on_folder_selected)
        self.add_file_btn.clicked.connect(self.add_files_to_folder)
        self.upload_btn.clicked.connect(self.upload_folder)

        # Load folders from config
        self.load_folders_from_config()

    def load_folders_from_config(self):
        """Load virtual folders from config and convert file paths to Path objects."""
        raw_folders = self.config_manager.data.get("virtual_folders", {})
        self.virtual_folders = {}
        for folder, file_list in raw_folders.items():
            # convert each string path to Path object
            self.virtual_folders[folder] = [Path(f) for f in file_list]
            self.folder_list.addItem(folder)

    def save_folders_to_config(self):
        """Convert Path objects to strings before saving JSON."""
        json_safe_folders = {}
        for folder, file_list in self.virtual_folders.items():
            json_safe_folders[folder] = [str(f) for f in file_list]
        self.config_manager.data["virtual_folders"] = json_safe_folders
        self.config_manager.save_config()

    def on_folder_selected(self, folder_name):
        self.current_folder = folder_name
        self.file_list.clear()
        if folder_name:
            self.add_file_btn.setEnabled(True)
            self.upload_btn.setEnabled(len(self.virtual_folders[folder_name]) > 0)
            for file_path in self.virtual_folders[folder_name]:
                self.add_file_item(file_path)
        else:
            self.add_file_btn.setEnabled(False)
            self.upload_btn.setEnabled(False)

    def add_files_to_folder(self):
        if not self.current_folder:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if not files:
            return

        for f in files:
            path = Path(f)
            # store Path internally but compare with string to avoid duplicates
            if path not in self.virtual_folders[self.current_folder]:
                self.virtual_folders[self.current_folder].append(path)
                self.add_file_item(path)

        self.upload_btn.setEnabled(True)
        self.save_folders_to_config()

    def create_virtual_folder(self):
        folder_name, ok = QInputDialog.getText(self, "New Virtual Folder", "Enter folder name:")
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()
        if folder_name in self.virtual_folders:
            QMessageBox.warning(self, "Exists", "A folder with that name already exists.")
            return
        self.virtual_folders[folder_name] = []
        self.folder_list.addItem(folder_name)
        self.save_folders_to_config()

    def add_file_item(self, path):
        lw_item = QListWidgetItem(path.name)
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
            pixmap = QPixmap(str(path))
            lw_item.setIcon(QIcon(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)))
        self.file_list.addItem(lw_item)

    def upload_folder(self):
        print(f"[DEBUG] Starting upload for folder: {self.current_folder}")
        if not self.current_folder:
            print("[DEBUG] No current folder selected")
            return

        files = self.virtual_folders.get(self.current_folder, [])
        print(f"[DEBUG] Files to upload: {[f.name for f in files]}")
        if not files:
            print("[DEBUG] Folder empty, aborting upload")
            QMessageBox.information(self, "Empty", "No files to upload.")
            return

        cfg = self.config_manager.load_config()
        username = cfg.get("username")
        token = cfg.get("token")
        if not username or not token:
            print("[DEBUG] Missing GitHub credentials")
            QMessageBox.warning(self, "Auth missing", "Enter GitHub username & token first.")
            return

        import base64
        from urllib.parse import quote

        repo_name = self.current_folder
        headers = {"Authorization": f"token {token}"}

        # Create repo if missing
        repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
        try:
            r = requests.get(repo_url, headers=headers)
            print(f"[DEBUG] GET repo status: {r.status_code}")
            if r.status_code == 404:
                print("[DEBUG] Repo not found, creating...")
                payload = {"name": repo_name, "private": False}
                r_create = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
                print(f"[DEBUG] POST create repo status: {r_create.status_code}")
                if r_create.status_code not in (200, 201):
                    print(f"[DEBUG] Failed to create repo: {r_create.json()}")
                    QMessageBox.critical(self, "Error",
                                         f"Cannot create repo:\n{r_create.status_code}\n{r_create.json()}")
                    return
        except Exception as e:
            print(f"[DEBUG] Exception checking/creating repo: {e}")
            QMessageBox.critical(self, "Error", f"Exception checking/creating repo:\n{e}")
            return

        # Upload files
        total_size = sum(f.stat().st_size for f in files)
        uploaded = 0
        self.progress.setValue(0)

        for f in files:
            print(f"[DEBUG] Uploading file: {f.name}")
            try:
                content = f.read_bytes()
            except Exception as e:
                print(f"[DEBUG] Cannot read {f.name}: {e}")
                QMessageBox.warning(self, "Read Error", f"Cannot read {f.name}:\n{e}")
                continue

            encoded = base64.b64encode(content).decode()
            file_path = quote(f.name)
            url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"

            try:
                r_check = requests.get(url, headers=headers)
                print(f"[DEBUG] GET file status: {r_check.status_code}")
                payload = {"message": f"Add {f.name}", "content": encoded}
                if r_check.status_code == 200:
                    payload["sha"] = r_check.json()["sha"]

                r_file = requests.put(url, headers=headers, json=payload)
                print(f"[DEBUG] PUT file status: {r_file.status_code}")
                if r_file.status_code not in (200, 201):
                    print(f"[DEBUG] Failed upload: {r_file.json()}")
                    QMessageBox.warning(self, "Upload Failed", f"Failed to upload {f.name}:\n{r_file.json()}")
                    continue
            except Exception as e:
                print(f"[DEBUG] Exception uploading {f.name}: {e}")
                QMessageBox.warning(self, "Network Error", f"Error uploading {f.name}:\n{e}")
                continue

            uploaded += f.stat().st_size
            perc = int(uploaded / total_size * 100)
            self.progress.setValue(perc)
            QApplication.processEvents()

        self.progress.setValue(100)
        print(f"[DEBUG] Upload complete for folder: {self.current_folder}")
        QMessageBox.information(self, "Backup Complete", f"Virtual folder '{self.current_folder}' uploaded to GitHub.")


# ---------- Main ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        # Config manager first
        self.config_manager = ConfigManager()

        # Create pages
        self.onboarding_page = OnboardingPage(self.show_auth, self.config_manager)
        self.auth_page = AuthPage(self.show_dashboard, self.config_manager)
        self.backup_page = BackupPage(self.config_manager)
        self.restore_page = RestorePage()
        self.settings_page = SettingsPage(self.config_manager)
        self.dashboard_page = DashboardPage(self.config_manager)

        # Main stack
        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        # Add pages
        self.mainStack.addWidget(self.onboarding_page)   # index 0
        self.mainStack.addWidget(self.auth_page)         # index 1
        # you could add a consolidated dashboard stack, for simplicity add a Dashboard as index 2:
        self.mainStack.addWidget(self.dashboard_page)    # index 2

        # Decide which page to show
        cfg = self.config_manager.load_config()
        onboarding_done = cfg.get("onboarding_done", False)
        token = cfg.get("token", "")

        if not onboarding_done:
            self.mainStack.setCurrentIndex(0)  # show onboarding
        elif token:
            self.mainStack.setCurrentIndex(2)  # skip auth, go to dashboard
        else:
            self.mainStack.setCurrentIndex(1)  # show auth

        self.apply_styles()

    def show_auth(self):
        self.mainStack.setCurrentIndex(1)

    def show_dashboard(self):
        self.mainStack.setCurrentIndex(2)

    def apply_styles(self):
        self.setStyleSheet(stylesheet)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 640)
    window.show()
    sys.exit(app.exec())
