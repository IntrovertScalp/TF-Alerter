from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint


class OverlayClock(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("00:00:00")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self._dragging = False
        self._drag_pos = QPoint()
        self.main_window = None  # Будет установлено из main.py

    def set_time(self, time_str):
        self.label.setText(time_str)

    def update_style(self, color, size, alpha=255):
        # Конвертируем цвет в RGBA с прозрачностью
        # Если цвет имеет формат #RRGGBBAA, используем его как есть
        if len(color) == 9:  # #RRGGBBAA формат
            rgba_color = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {alpha})"
        else:  # #RRGGBB формат
            rgba_color = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {alpha})"

        # Чистый прозрачный фон. Тянуть можно только за прорисованные части цифр.
        self.label.setStyleSheet(
            f"""
            color: {rgba_color}; 
            font-size: {size}px; 
            font-weight: bold; 
            background: transparent;
        """
        )
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.pos()
            self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.releaseMouse()
            # Сохраняем позицию после перетаскивания
            if self.main_window:
                self.main_window.save_settings()
            event.accept()
