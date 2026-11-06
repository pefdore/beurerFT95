"""Widget rond bleu (style miscale) affichant la dernière température du FT95."""
from __future__ import annotations

import queue
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

WIDGET_SIZE = 64
COLOR_BACKGROUND = "#00264c"
COLOR_CONTOUR = "white"
COLOR_TEXT = "white"
ANCHOR_X_PERCENT = 52
ANCHOR_Y_PERCENT = 4.6
ANCHOR_POINT_IS_CENTER = True


class TempWidget(QWidget):
    def __init__(self, data_queue: "queue.Queue[str]"):
        super().__init__()
        self.data_queue = data_queue
        self.current_temp = "--.-"
        self.screen_geometry = QApplication.primaryScreen().geometry()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("FT95Widget")
        self.resize(WIDGET_SIZE, WIDGET_SIZE)
        font_size = int(WIDGET_SIZE / 5.5)
        self.pen_width = max(int(WIDGET_SIZE / 30), 1)
        self.font = QFont("Arial", font_size, QFont.Bold)

        timer = QTimer(self)
        timer.timeout.connect(self.process_queue)
        timer.start(50)
        self.position_on_screen()
        self.show()

    def position_on_screen(self) -> None:
        sw, sh = self.screen_geometry.width(), self.screen_geometry.height()
        tx, ty = sw * ANCHOR_X_PERCENT / 100, sh * ANCHOR_Y_PERCENT / 100
        fx, fy = (tx - self.width() / 2, ty - self.height() / 2) if ANCHOR_POINT_IS_CENTER else (tx, ty)
        self.move(int(fx), int(fy))

    def process_queue(self) -> None:
        try:
            while True:
                value = self.data_queue.get_nowait()
                if value != self.current_temp:
                    self.current_temp = value
                    self.update()
        except queue.Empty:
            pass

    def mousePressEvent(self, event) -> None:
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if getattr(self, "oldPos", None) is not None:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPosition().toPoint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(COLOR_CONTOUR), self.pen_width))
        painter.setBrush(QColor(COLOR_BACKGROUND))
        offset = self.pen_width
        painter.drawEllipse(offset, offset, self.width() - offset * 2, self.height() - offset * 2)
        painter.setPen(QPen(QColor(COLOR_TEXT)))
        painter.setFont(self.font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.current_temp)


def run_widget(ble_thread_target) -> None:
    data_queue: "queue.Queue[str]" = queue.Queue()
    threading.Thread(target=ble_thread_target, args=(data_queue,), daemon=True).start()
    app = QApplication(sys.argv)
    TempWidget(data_queue)
    sys.exit(app.exec())
