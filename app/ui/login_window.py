"""
Login window UI matching the provided design.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QMouseEvent
from ..config import (
    COLOR_PRIMARY, COLOR_TEXT_DARK, COLOR_TEXT_LIGHT, 
    COLOR_BACKGROUND, COLOR_BACKGROUND_DARK, COLOR_BORDER_LIGHT,
    WINDOW_WIDTH, WINDOW_HEIGHT
)


class LoginWindow(QWidget):
    """Login window matching the design."""
    
    login_requested = Signal(str, str, bool)  # email, password, remember_me
    
    def __init__(self):
        super().__init__()
        self._drag_position = QPoint()
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        # Set window flags for frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # Dark grey background for the window
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND_DARK};
            }}
        """)
        
        # Main layout with dark background
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # White card container with rounded corners
        card_container = QWidget()
        card_container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND};
                border-radius: 25px;
            }}
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(40, 40, 40, 32)
        card_layout.setSpacing(0)
        card_container.setLayout(card_layout)
        main_layout.addWidget(card_container)
        
        # Store card_layout reference for adding widgets
        self.card_layout = card_layout
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        welcome_label = QLabel("Welcome")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_font = QFont()
        welcome_font.setPointSize(18)
        welcome_font.setWeight(QFont.Weight.Normal)
        welcome_label.setFont(welcome_font)
        welcome_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        
        subtitle_label = QLabel("Login to your account")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT};")
        
        header_layout.addWidget(welcome_label)
        header_layout.addWidget(subtitle_label)
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self.card_layout.addWidget(header_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BORDER_LIGHT};
                max-height: 1px;
                min-height: 1px;
                border: none;
                margin: 0;
                padding: 0;
            }}
        """)
        self.card_layout.addWidget(separator)
        
        # Email field
        email_layout = QVBoxLayout()
        email_layout.setSpacing(0)
        email_layout.setContentsMargins(0, 0, 0, 0)
        
        email_label = QLabel("Enter Your Email")
        email_label_font = QFont()
        email_label_font.setPointSize(12)
        email_label.setFont(email_label_font)
        email_label.setStyleSheet(f"color: {COLOR_TEXT_DARK}; margin: 0; padding: 0;")
        email_label.setContentsMargins(0, 0, 0, 0)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("")
        self.email_input.setFixedHeight(40)
        self.email_input.setMinimumWidth(280)
        self.email_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                color: {COLOR_TEXT_DARK};
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
        """)
        
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        email_widget = QWidget()
        email_widget.setLayout(email_layout)
        self.card_layout.addWidget(email_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Password field (with eye toggle)
        password_layout = QVBoxLayout()
        password_layout.setSpacing(0)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        password_label = QLabel("Enter Your Password")
        password_label_font = QFont()
        password_label_font.setPointSize(12)
        password_label.setFont(password_label_font)
        password_label.setStyleSheet(f"color: {COLOR_TEXT_DARK}; margin: 0; padding: 0;")
        password_label.setContentsMargins(0, 0, 0, 0)
        
        password_field_row = QHBoxLayout()
        password_field_row.setSpacing(0)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("")
        self.password_input.setFixedHeight(40)
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
                padding: 10px 12px 10px 12px;
                font-size: 14px;
                color: {COLOR_TEXT_DARK};
            }}
            QLineEdit:focus {{
                border: 2px solid {COLOR_PRIMARY};
            }}
        """)
        self.password_input.setMinimumWidth(240)
        
        self._password_toggle_btn = QPushButton("👁")
        self._password_toggle_btn.setFixedSize(40, 40)
        self._password_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._password_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                font-size: 16px;
                color: {COLOR_TEXT_LIGHT};
            }}
            QPushButton:hover {{
                background-color: #f5f5f5;
                color: {COLOR_TEXT_DARK};
            }}
        """)
        self._password_toggle_btn.clicked.connect(self._toggle_password_visibility)
        
        password_field_row.addWidget(self.password_input, 1)
        password_field_row.addWidget(self._password_toggle_btn)
        
        password_layout.addWidget(password_label)
        password_layout.addLayout(password_field_row)
        password_widget = QWidget()
        password_widget.setLayout(password_layout)
        self.card_layout.addWidget(password_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Options row
        options_layout = QHBoxLayout()
        options_layout.setSpacing(0)
        options_layout.setContentsMargins(0, 0, 0, 0)
        
        self.remember_checkbox = QCheckBox("Remember Me")
        remember_font = QFont()
        remember_font.setPointSize(10)
        self.remember_checkbox.setFont(remember_font)
        self.remember_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {COLOR_TEXT_DARK};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {COLOR_BORDER_LIGHT};
                border-radius: 3px;
                background-color: {COLOR_BACKGROUND};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLOR_PRIMARY};
                border-color: {COLOR_PRIMARY};
            }}
        """)
        
        recover_button = QPushButton("Recover Password")
        recover_font = QFont()
        recover_font.setPointSize(10)
        recover_button.setFont(recover_font)
        recover_button.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_PRIMARY};
                background-color: transparent;
                border: none;
                text-align: right;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        recover_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        options_layout.addWidget(self.remember_checkbox)
        options_layout.addStretch()
        options_layout.addWidget(recover_button)
        options_widget = QWidget()
        options_widget.setLayout(options_layout)
        options_widget.setMinimumWidth(280)
        self.card_layout.addWidget(options_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        # Loading indicator (hidden by default)
        self._loading_widget = QWidget()
        self._loading_widget.setMinimumWidth(280)
        loading_layout = QVBoxLayout()
        loading_layout.setSpacing(0)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        self._loading_label = QLabel("Signing in...")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_font = QFont()
        loading_font.setPointSize(12)
        self._loading_label.setFont(loading_font)
        self._loading_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        self._loading_progress = QProgressBar()
        self._loading_progress.setRange(0, 0)  # Indeterminate
        self._loading_progress.setFixedHeight(6)
        self._loading_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background: {COLOR_BORDER_LIGHT};
            }}
            QProgressBar::chunk {{
                background: {COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        loading_layout.addWidget(self._loading_label)
        loading_layout.addWidget(self._loading_progress)
        self._loading_widget.setLayout(loading_layout)
        self._loading_widget.hide()
        self.card_layout.addWidget(self._loading_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumWidth(280)
        login_font = QFont()
        login_font.setPointSize(14)
        self.login_button.setFont(login_font)
        self.login_button.setFixedHeight(50)
        self.login_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5a4abd;
            }}
            QPushButton:pressed {{
                background-color: #4a3a9d;
            }}
        """)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._on_login_clicked)
        
        # Allow Enter key to trigger login
        self.password_input.returnPressed.connect(self._on_login_clicked)
        
        self.card_layout.addWidget(self.login_button, 0, Qt.AlignmentFlag.AlignHCenter)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            self._drag_position = event.globalPosition().toPoint() - win.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            win = self.window()
            new_pos = event.globalPosition().toPoint() - self._drag_position
            win.move(new_pos)
            event.accept()
    
    def _toggle_password_visibility(self):
        """Toggle password field between masked and visible."""
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._password_toggle_btn.setText("🙈")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._password_toggle_btn.setText("👁")

    def _on_login_clicked(self):
        """Handle login button click."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        remember_me = self.remember_checkbox.isChecked()
        
        if email and password:
            self.login_requested.emit(email, password, remember_me)
    
    def set_loading(self, loading: bool):
        """Disable inputs, show loader and 'Signing in...' while an API call is in progress."""
        self.email_input.setEnabled(not loading)
        self.password_input.setEnabled(not loading)
        self._password_toggle_btn.setEnabled(not loading)
        self.login_button.setEnabled(not loading)
        self._loading_widget.setVisible(loading)
        if loading:
            self.login_button.setText("Signing in...")
            self.login_button.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.login_button.setText("Login")
            self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def show_error(self, message: str):
        """Show error message (can be enhanced with a label)."""
        print(f"Login error: {message}")
    
    def clear_fields(self):
        """Clear input fields."""
        self.email_input.clear()
        self.password_input.clear()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_toggle_btn.setText("👁")
        self.remember_checkbox.setChecked(False)
