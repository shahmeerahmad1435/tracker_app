"""
Dashboard window UI matching the provided design.
Shows different states: Checked In, On Break, Force Break, Checked Out.
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QPointF, QSize
from PySide6.QtGui import QFont, QIcon, QImage, QPixmap, QPainter, QColor, QMouseEvent
from PySide6.QtSvg import QSvgRenderer
from ..config import (
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_ALERT, COLOR_TEXT_DARK, 
    COLOR_TEXT_LIGHT, COLOR_BACKGROUND, COLOR_BACKGROUND_DARK, COLOR_BORDER_LIGHT,
    WINDOW_WIDTH, WINDOW_HEIGHT
)
from ..state_manager import AppState


def _to_local_naive(dt: datetime):
    """Convert timezone-aware datetime to local naive for use with datetime.now()."""
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


class DashboardWindow(QWidget):
    """Dashboard window matching the design."""
    
    logout_requested = Signal()
    check_in_requested = Signal()
    check_out_requested = Signal()
    start_break_requested = Signal()
    end_break_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_time)
        self._timer.start(1000)  # Update every second
        self._check_in_timestamp = None
        self._break_start_timestamp = None  # When set, timer is frozen (on break)
        self._today_attendance_breaks = None  # List of (start_dt, end_dt) for work time = elapsed - breaks
        self._drag_position = QPoint()
        self._was_checked_in = False  # Track if user was previously checked in
        
        # Get assets directory path (support PyInstaller frozen bundle)
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "app"
        else:
            base = Path(__file__).resolve().parent.parent
        self._assets_dir = base / "assets"
        
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
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)
        card_container.setLayout(card_layout)
        main_layout.addWidget(card_container)
        
        # Use card_layout for all content
        self.card_layout = card_layout
        
        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 20)
        
        logout_button = QPushButton()
        logout_button.setFixedSize(32, 32)
        logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: transparent;
            }}
        """)
        logout_button.setIcon(self._create_icon("power", COLOR_TEXT_DARK, 20))
        logout_button.setIconSize(logout_button.size())
        logout_button.clicked.connect(self.logout_requested.emit)
        logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        top_bar.addWidget(logout_button)
        top_bar.addStretch()
        self.card_layout.addLayout(top_bar)
        
        # Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(40, 20, 40, 20)

        # Loading indicator (hidden by default)
        self._loading_widget = QWidget()
        loading_layout = QVBoxLayout()
        loading_layout.setSpacing(6)
        self._loading_label = QLabel("Loading...")
        self._loading_label.setAlignment(Qt.AlignCenter)
        loading_font = QFont()
        loading_font.setPointSize(12)
        self._loading_label.setFont(loading_font)
        self._loading_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT};")
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
        content_layout.addWidget(self._loading_widget)
        
        # Welcome label
        self.welcome_label = QLabel("Welcome")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        welcome_font = QFont()
        welcome_font.setPointSize(16)
        self.welcome_label.setFont(welcome_font)
        self.welcome_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        content_layout.addWidget(self.welcome_label)
        
        # User name label
        self.user_name_label = QLabel("User Name")
        self.user_name_label.setAlignment(Qt.AlignCenter)
        user_font = QFont()
        user_font.setPointSize(24)
        user_font.setWeight(QFont.Weight.DemiBold)
        self.user_name_label.setFont(user_font)
        self.user_name_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        content_layout.addWidget(self.user_name_label)
        
        # Time display
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(56)
        time_font.setWeight(QFont.Weight.Bold)
        self.time_label.setFont(time_font)
        self.time_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        content_layout.addWidget(self.time_label)
        
        # Shift label (set via set_shift_info from staff/dashboard or login staff_settings)
        self.shift_label = QLabel("Your Shift")
        self.shift_label.setAlignment(Qt.AlignCenter)
        shift_font = QFont()
        shift_font.setPointSize(12)
        self.shift_label.setFont(shift_font)
        self.shift_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT};")
        content_layout.addWidget(self.shift_label)
        
        # Status area
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(20)
        status_font.setWeight(QFont.Weight.DemiBold)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_label)
        
        self.status_time_label = QLabel("")
        self.status_time_label.setAlignment(Qt.AlignCenter)
        status_time_font = QFont()
        status_time_font.setPointSize(14)
        self.status_time_label.setFont(status_time_font)
        self.status_time_label.setStyleSheet(f"color: {COLOR_TEXT_LIGHT};")
        status_layout.addWidget(self.status_time_label)
        
        # Late badge
        self.late_badge = QLabel("")
        self.late_badge.setAlignment(Qt.AlignCenter)
        late_font = QFont()
        late_font.setPointSize(10)
        self.late_badge.setFont(late_font)
        self.late_badge.setStyleSheet(f"""
            QLabel {{
                background-color: #f0f0f0;
                color: {COLOR_TEXT_LIGHT};
                border-radius: 12px;
                padding: 4px 12px;
            }}
        """)
        self.late_badge.hide()
        status_layout.addWidget(self.late_badge)
        
        content_layout.addLayout(status_layout)
        
        self.card_layout.addLayout(content_layout)
        
        # Spacer
        self.card_layout.addStretch()
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(30)
        buttons_layout.setContentsMargins(40, 20, 40, 20)
        
        # Check-in/Check-out button
        self.check_in_out_button = QPushButton()
        self.check_in_out_button.setFixedSize(120, 120)
        self.check_in_out_button.setStyleSheet(f"""
            QPushButton {{
                border-radius: 60px;
                border: none;
            }}
        """)
        self.check_in_out_button.clicked.connect(self._on_check_in_out_clicked)
        self.check_in_out_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.check_in_out_label = QLabel("Check-in")
        self.check_in_out_label.setAlignment(Qt.AlignCenter)
        button_label_font = QFont()
        button_label_font.setPointSize(12)
        self.check_in_out_label.setFont(button_label_font)
        self.check_in_out_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        
        check_in_out_layout = QVBoxLayout()
        check_in_out_layout.setSpacing(8)
        check_in_out_layout.setAlignment(Qt.AlignCenter)
        check_in_out_layout.addWidget(self.check_in_out_button)
        check_in_out_layout.addWidget(self.check_in_out_label)
        
        # Break button
        self.break_button = QPushButton()
        self.break_button.setFixedSize(120, 120)
        self.break_button.setStyleSheet(f"""
            QPushButton {{
                border-radius: 60px;
                border: 2px solid {COLOR_TEXT_LIGHT};
                background-color: {COLOR_BACKGROUND};
            }}
        """)
        self.break_button.clicked.connect(self._on_break_clicked)
        self.break_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.break_label = QLabel("Break")
        self.break_label.setAlignment(Qt.AlignCenter)
        self.break_label.setFont(button_label_font)
        self.break_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
        
        break_layout = QVBoxLayout()
        break_layout.setSpacing(8)
        break_layout.setAlignment(Qt.AlignCenter)
        break_layout.addWidget(self.break_button)
        break_layout.addWidget(self.break_label)
        
        buttons_layout.addLayout(check_in_out_layout)
        buttons_layout.addStretch()
        buttons_layout.addLayout(break_layout)
        
        self.card_layout.addLayout(buttons_layout)
        
        # Set initial state
        self.update_state(AppState.LOGGED_OUT)
    
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
    
    def _load_svg_icon(self, icon_name: str, color: str, size: int = 32) -> QIcon:
        """Load SVG icon from assets folder and apply color."""
        svg_path = self._assets_dir / f"{icon_name}.svg"
        
        # Check if SVG file exists
        if not svg_path.exists():
            # Fallback to programmatic icon if SVG not found
            return self._create_fallback_icon(icon_name, color, size)
        
        try:
            # Read SVG file
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Replace colors with desired color
            # Handle various color formats and patterns
            import re
            
            # Replace currentColor
            svg_content = svg_content.replace('currentColor', color)
            
            # Replace stroke colors (handle quotes and hex colors)
            svg_content = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', svg_content)
            svg_content = re.sub(r"stroke='[^']*'", f"stroke='{color}'", svg_content)
            
            # Replace fill colors (handle quotes and hex colors)
            svg_content = re.sub(r'fill="[^"]*"', f'fill="{color}"', svg_content)
            svg_content = re.sub(r"fill='[^']*'", f"fill='{color}'", svg_content)
            
            # Also handle common hardcoded colors
            svg_content = svg_content.replace('fill="white"', f'fill="{color}"')
            svg_content = svg_content.replace("fill='white'", f"fill='{color}'")
            svg_content = svg_content.replace('fill="#ffffff"', f'fill="{color}"')
            svg_content = svg_content.replace('fill="#FFFFFF"', f'fill="{color}"')
            svg_content = svg_content.replace('fill="black"', f'fill="{color}"')
            svg_content = svg_content.replace("fill='black'", f"fill='{color}'")
            svg_content = svg_content.replace('fill="#000000"', f'fill="{color}"')
            svg_content = svg_content.replace('fill="#404040"', f'fill="{color}"')
            
            svg_content = svg_content.replace('stroke="white"', f'stroke="{color}"')
            svg_content = svg_content.replace("stroke='white'", f"stroke='{color}'")
            svg_content = svg_content.replace('stroke="#ffffff"', f'stroke="{color}"')
            svg_content = svg_content.replace('stroke="black"', f'stroke="{color}"')
            svg_content = svg_content.replace("stroke='black'", f"stroke='{color}'")
            svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color}"')
            svg_content = svg_content.replace('stroke="#404040"', f'stroke="{color}"')
            
            # Create renderer
            renderer = QSvgRenderer(svg_content.encode('utf-8'))
            
            # Create pixmap and render SVG
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error loading SVG {icon_name}: {e}")
            # Fallback to programmatic icon
            return self._create_fallback_icon(icon_name, color, size)
    
    def _create_fallback_icon(self, icon_type: str, color: str, size: int = 32) -> QIcon:
        """Create fallback icon programmatically if SVG is not available."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        
        try:
            if icon_type == "power":
                center = size // 2
                radius = size // 3
                painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)
                line_width = 2
                painter.drawRect(center - line_width // 2, size // 4, line_width, size // 4)
            elif icon_type == "close":
                line_width = 2
                offset = size // 4
                painter.drawPolygon([
                    QPointF(offset, offset - line_width),
                    QPointF(size - offset, size - offset - line_width),
                    QPointF(size - offset, size - offset + line_width),
                    QPointF(offset, offset + line_width)
                ])
                painter.drawPolygon([
                    QPointF(size - offset, offset - line_width),
                    QPointF(offset, size - offset - line_width),
                    QPointF(offset, size - offset + line_width),
                    QPointF(size - offset, offset + line_width)
                ])
            elif icon_type == "arrow_right":
                center_y = size // 2
                arrow_width = size // 3
                arrow_height = size // 2
                start_x = size // 3
                points = [
                    QPointF(start_x, center_y - arrow_height // 2),
                    QPointF(start_x + arrow_width, center_y),
                    QPointF(start_x, center_y + arrow_height // 2),
                    QPointF(start_x + arrow_width // 3, center_y)
                ]
                painter.drawPolygon(points)
            elif icon_type == "arrow_left":
                center_y = size // 2
                arrow_width = size // 3
                arrow_height = size // 2
                start_x = size - size // 3
                points = [
                    QPointF(start_x, center_y - arrow_height // 2),
                    QPointF(start_x - arrow_width, center_y),
                    QPointF(start_x, center_y + arrow_height // 2),
                    QPointF(start_x - arrow_width // 3, center_y)
                ]
                painter.drawPolygon(points)
            elif icon_type == "pause":
                bar_width = size // 6
                bar_height = size // 2
                bar_y = (size - bar_height) // 2
                painter.drawRoundedRect(size // 4 - bar_width // 2, bar_y, bar_width, bar_height, 1, 1)
                painter.drawRoundedRect(3 * size // 4 - bar_width // 2, bar_y, bar_width, bar_height, 1, 1)
            elif icon_type == "play":
                center_y = size // 2
                triangle_width = size // 2.5
                triangle_height = size // 2
                start_x = size // 4
                points = [
                    QPointF(start_x, center_y - triangle_height // 2),
                    QPointF(start_x + triangle_width, center_y),
                    QPointF(start_x, center_y + triangle_height // 2)
                ]
                painter.drawPolygon(points)
        finally:
            painter.end()
        
        return QIcon(pixmap)
    
    def _load_png_icon(self, icon_name: str, color: str, size: int = 32) -> QIcon:
        """Load PNG icon (arrow_left, arrow_right), scale to size, and optionally tint to color."""
        png_path = self._assets_dir / f"{icon_name}.png"
        if not png_path.exists():
            return self._load_svg_icon(icon_name, color, size)

        try:
            img = QImage(str(png_path))
            if img.isNull():
                return self._load_svg_icon(icon_name, color, size)
            img = img.convertToFormat(QImage.Format.Format_ARGB32)
            img = img.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            # Tint non-white pixels to the requested color (PNG is white-on-transparent)
            need_tint = color.lower() not in ("white", "#ffffff", "#fff")
            if need_tint:
                qc = QColor(color)
                if not qc.isValid():
                    qc = QColor(COLOR_TEXT_DARK)
                r, g, b = qc.red(), qc.green(), qc.blue()
                for y in range(img.height()):
                    for x in range(img.width()):
                        p = img.pixelColor(x, y)
                        if p.alpha() > 10:
                            img.setPixelColor(x, y, QColor(r, g, b, p.alpha()))

            return QIcon(QPixmap.fromImage(img))
        except Exception as e:
            print(f"Error loading PNG {icon_name}: {e}")
            return self._load_svg_icon(icon_name, color, size)

    def _create_icon(self, icon_type: str, color: str, size: int = 32) -> QIcon:
        """Create icon - PNG for arrow_left/arrow_right, else SVG, then programmatic fallback."""
        if icon_type in ("arrow_left", "arrow_right"):
            png_path = self._assets_dir / f"{icon_type}.png"
            if png_path.exists():
                return self._load_png_icon(icon_type, color, size)
        return self._load_svg_icon(icon_type, color, size)
    
    def _update_time(self):
        """Show work time = (check_in to now or break_start) minus all break durations (HH:MM:SS)."""
        try:
            if self._check_in_timestamp is None:
                self.time_label.setText("00:00:00")
                return
            
            now = datetime.now()
            if self._break_start_timestamp is not None:
                end_dt = self._break_start_timestamp  # Frozen on break
            else:
                end_dt = now
            
            elapsed_seconds = (end_dt - self._check_in_timestamp).total_seconds()
            break_seconds = self._total_break_seconds(end_dt)
            work_seconds = max(0, int(elapsed_seconds - break_seconds))
            
            hours = work_seconds // 3600
            minutes = (work_seconds % 3600) // 60
            seconds = work_seconds % 60
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        except Exception as e:
            print(f"Timer error: {e}")
            self.time_label.setText("00:00:00")
    
    def _total_break_seconds(self, as_of_dt: datetime) -> float:
        """Total break duration in seconds up to as_of_dt. Uses today_attendance breaks (start_time, end_time)."""
        if not self._today_attendance_breaks:
            return 0.0
        total = 0.0
        for start_dt, end_dt in self._today_attendance_breaks:
            if end_dt is not None:
                if end_dt <= as_of_dt:
                    total += (end_dt - start_dt).total_seconds()
            else:
                # Current/open break: duration from start to as_of_dt
                if start_dt < as_of_dt:
                    total += (as_of_dt - start_dt).total_seconds()
        return total
    
    def set_today_attendance(self, today_attendance: dict):
        """Set today_attendance from API; parse breaks into (start_dt, end_dt) for work time calculation."""
        self._today_attendance_breaks = None
        if not today_attendance:
            return
        breaks_raw = today_attendance.get("breaks") or []
        parsed = []
        for b in breaks_raw:
            if not isinstance(b, dict):
                continue
            start_iso = b.get("start_time") or b.get("start")
            if not start_iso:
                continue
            try:
                start_dt = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
                start_dt = _to_local_naive(start_dt)
            except Exception:
                continue
            end_iso = b.get("end_time") or b.get("end")
            end_dt = None
            if end_iso:
                try:
                    end_dt = datetime.fromisoformat(str(end_iso).replace("Z", "+00:00"))
                    end_dt = _to_local_naive(end_dt)
                except Exception:
                    pass
            parsed.append((start_dt, end_dt))
        self._today_attendance_breaks = parsed
    
    def set_check_in_time(self, check_in_time_str: str = None, check_in_timestamp: datetime = None,
                          break_start_timestamp: datetime = None):
        """Set check-in time and optional break freeze for timer.
        
        Args:
            check_in_time_str: Time string in HH:MM format (fallback if no timestamp)
            check_in_timestamp: datetime for check-in (from API or now); API datetimes are converted to local
            break_start_timestamp: if set, timer is frozen at (break_start - check_in); when None, no freeze
        """
        if check_in_timestamp is not None:
            self._check_in_timestamp = _to_local_naive(check_in_timestamp)
        elif check_in_time_str:
            try:
                hour, minute = map(int, check_in_time_str.split(':'))
                self._check_in_timestamp = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            except Exception:
                self._check_in_timestamp = datetime.now()
        # if both None: keep existing _check_in_timestamp (e.g. when only clearing break)
        
        self._break_start_timestamp = _to_local_naive(break_start_timestamp) if break_start_timestamp is not None else None
    
    def set_break_freeze(self, break_start_timestamp: datetime):
        """Freeze timer when user goes on break. Display = (break_start - check_in)."""
        self._break_start_timestamp = break_start_timestamp
    
    def clear_break_freeze(self):
        """Resume timer when user ends break. Display = (now - check_in)."""
        self._break_start_timestamp = None
    
    def reset_timer(self):
        """Reset the timer (when checking out or logging out). Shows 00:00:00."""
        self._check_in_timestamp = None
        self._break_start_timestamp = None
    
    def set_actions_loading(self, loading: bool):
        """Disable action buttons, show loader and wait cursor while an API call is in progress."""
        self._loading_widget.setVisible(loading)
        self.check_in_out_button.setEnabled(not loading)
        self.break_button.setEnabled(not loading)
        if loading:
            self.check_in_out_button.setCursor(Qt.CursorShape.WaitCursor)
            self.break_button.setCursor(Qt.CursorShape.WaitCursor)
        else:
            self.check_in_out_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.break_button.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_user_name(self, name: str):
        """Set user name."""
        self.user_name_label.setText(name)

    def set_shift_info(self, shift_start: str = "", shift_end: str = "", timezone: str = "UTC"):
        """Set shift label from staff: 'Your Shift (TZ)' or 'Your Shift (TZ) HH:MM - HH:MM'."""
        tz = timezone or "UTC"
        if shift_start and shift_end:
            self.shift_label.setText(f"Your Shift ({tz})  {shift_start} - {shift_end}")
        else:
            self.shift_label.setText(f"Your Shift ({tz})")

    def set_was_checked_in(self, value: bool):
        """When True, LOGGED_OUT shows 'Checked Out'; when False, neutral (no status)."""
        self._was_checked_in = value

    def update_state(self, state: AppState, check_in_time: str = None, 
                    break_start_time: str = None, late_by_minutes: int = None):
        """Update UI based on state."""
        # Only reset timer when logging out or checking out
        if state == AppState.LOGGED_OUT:
            self.reset_timer()
        
        if state == AppState.LOGGED_OUT:
            # Show "Checked Out" if user was previously checked in, otherwise show nothing
            if self._was_checked_in:
                self.status_label.setText("Checked Out")
                self.status_label.setStyleSheet(f"color: {COLOR_TEXT_DARK};")
                self.status_label.show()
                self.status_time_label.hide()
                self.late_badge.hide()
                # Keep flag True to continue showing "Checked Out" until next check-in
            else:
                self.status_label.setText("")
                self.status_label.hide()
                self.status_time_label.setText("")
                self.status_time_label.hide()
                self.late_badge.hide()
            
            # Check-in button active
            self.check_in_out_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    border: none;
                    border-radius: 60px;
                }}
            """)
            self.check_in_out_button.setIcon(self._create_icon("arrow_right", "white", 60))
            self.check_in_out_button.setIconSize(self.check_in_out_button.size())
            self.check_in_out_label.setText("Check-in")
            self.check_in_out_button.setEnabled(True)
            
            # Break button inactive (label "Break" for both neutral and checked out)
            self.break_label.setText("Break")
            self.break_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BACKGROUND};
                    border: 2px solid {COLOR_BORDER_LIGHT};
                    border-radius: 60px;
                }}
            """)
            self.break_button.setIcon(self._create_icon("pause", COLOR_TEXT_DARK, 60))
            self.break_button.setIconSize(self.break_button.size())
            self.break_button.setEnabled(False)
            
        elif state == AppState.CHECKED_IN:
            # Resume timer when coming back from break
            self.clear_break_freeze()
            # Mark that user has checked in (so we can show "Checked Out" when they check out)
            self._was_checked_in = True
            self.status_label.setText("Checked In")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
            self.status_label.show()
            
            if check_in_time:
                self.status_time_label.setText(check_in_time)
                self.status_time_label.show()
            else:
                self.status_time_label.hide()
            
            if late_by_minutes and late_by_minutes > 0:
                self.late_badge.setText(f"Late by: {late_by_minutes} min")
                self.late_badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: #f0f0f0;
                        color: {COLOR_TEXT_LIGHT};
                        border: 1px solid {COLOR_BORDER_LIGHT};
                        border-radius: 12px;
                        padding: 4px 12px;
                    }}
                """)
                self.late_badge.show()
            else:
                self.late_badge.hide()
            
            # Check-out button active
            self.check_in_out_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    border: none;
                    border-radius: 60px;
                }}
            """)
            self.check_in_out_button.setIcon(self._create_icon("arrow_left", "white", 60))
            self.check_in_out_button.setIconSize(self.check_in_out_button.size())
            self.check_in_out_label.setText("Check-out")
            self.check_in_out_button.setEnabled(True)
            
            # Start Break button active
            self.break_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    border: none;
                    border-radius: 60px;
                }}
            """)
            self.break_button.setIcon(self._create_icon("pause", "white", 60))
            self.break_button.setIconSize(self.break_button.size())
            self.break_label.setText("Start Break")
            self.break_button.setEnabled(True)
            
        elif state == AppState.ON_BREAK or state == AppState.FORCE_BREAK:
            status_text = "Force Break" if state == AppState.FORCE_BREAK else "On Break"
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"color: {COLOR_ALERT};")
            self.status_label.show()
            
            if break_start_time:
                self.status_time_label.setText(break_start_time)
                self.status_time_label.show()
            else:
                self.status_time_label.hide()
            
            self.late_badge.hide()
            
            # Check-out button inactive
            self.check_in_out_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BACKGROUND};
                    border: 2px solid {COLOR_BORDER_LIGHT};
                    border-radius: 60px;
                }}
            """)
            self.check_in_out_button.setIcon(self._create_icon("arrow_left", COLOR_TEXT_DARK, 60))
            self.check_in_out_button.setIconSize(self.check_in_out_button.size())
            self.check_in_out_label.setText("Check-out")
            self.check_in_out_button.setEnabled(False)
            
            # End Break button active (red)
            self.break_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_ALERT};
                    border: none;
                    border-radius: 60px;
                }}
            """)
            self.break_button.setIcon(self._create_icon("play", "white", 60))
            self.break_button.setIconSize(self.break_button.size())
            self.break_label.setText("End Break")
            self.break_button.setEnabled(True)
        
    
    def _on_check_in_out_clicked(self):
        """Handle check-in/check-out button click."""
        if self.check_in_out_label.text() == "Check-in":
            self.check_in_requested.emit()
        else:
            self.check_out_requested.emit()
    
    def _on_break_clicked(self):
        """Handle break button click."""
        if self.break_label.text() in ["Break", "Start Break"]:
            self.start_break_requested.emit()
        else:
            self.end_break_requested.emit()
