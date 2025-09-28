import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QLineEdit
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
)

from core.config import ConfigManager
from core.const import stylesheet
from core.dashboard import DashboardPage
from core.auth import AuthPage
from core.backup import BackupPage
from core.restore import RestorePage
from core.settings import SettingsPage


class OnboardingPage(QWidget):
    def __init__(self, switch_to_auth, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.stack = QStackedWidget()
        self.pages = []

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

        if index < len(self.pages) - 1:
            self.stack.setCurrentIndex(index + 1)
        else:

            self.config_manager.data["onboarding_done"] = True
            self.config_manager.save_config()
            switch_to_auth()


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

            "onboarding_done": self.config_manager.data.get("onboarding_done", False)
        }
        self.config_manager.save_config(data)
        switch_to_dashboard()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PushBox")

        self.config_manager = ConfigManager()

        self.onboarding_page = OnboardingPage(self.show_auth, self.config_manager)
        self.auth_page = AuthPage(self.show_dashboard, self.config_manager)
        self.backup_page = BackupPage(self.config_manager)
        self.restore_page = RestorePage()
        self.settings_page = SettingsPage(self.config_manager)
        self.dashboard_page = DashboardPage(self.config_manager)

        self.mainStack = QStackedWidget()
        self.setCentralWidget(self.mainStack)

        self.mainStack.addWidget(self.onboarding_page)
        self.mainStack.addWidget(self.auth_page)

        self.mainStack.addWidget(self.dashboard_page)

        cfg = self.config_manager.load_config()
        onboarding_done = cfg.get("onboarding_done", False)
        token = cfg.get("token", "")

        if not onboarding_done:
            self.mainStack.setCurrentIndex(0)
        elif token:
            self.mainStack.setCurrentIndex(2)
        else:
            self.mainStack.setCurrentIndex(1)

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
