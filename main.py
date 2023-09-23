import sys
from functools import partial

import pyautogui as pya
import keyboard

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow, QTextEdit, QPushButton
from PySide6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, Signal, QPoint, QThread
from PySide6.QtGui import QFont, QIcon

from translate import translate_text
from tkinter import Tk


def copy_clipboard():
    with pya.hold('ctrl'):
        pya.press(['c'])
    return Tk().clipboard_get()


# Define the hotkey combination
hotkey_combination = ["ctrl", 'shift', "c"]


class WaitHotKey(QThread):
    text = Signal(str)

    def __init__(self, parent):
        super(WaitHotKey, self).__init__(parent=parent)
        self.parent = parent

    def run(self):
        while True:
            if all(keyboard.is_pressed(key) for key in hotkey_combination):
                text = copy_clipboard()
                self.text.emit(translate_text(text))


class AutoTranslate(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.wait_hotkey = WaitHotKey(self)
        self.wait_hotkey.text.connect(self.translate)
        self.wait_hotkey.start()

        self.notify = NotificationManager(self.app, "center")
        print("Run app!")

    def translate(self, text):
        self.notify.show_notification("", text)


class Notification(QWidget):
    finished = Signal()

    def __init__(self, title, message, parent, notification_count):
        super().__init__(parent=parent)
        self.moved = None
        self.parent: NotificationManager = parent
        self.title = title
        self.message = message

        self.setWindowTitle(title)
        self.setGeometry(0, 0, 320, 250)
        self.setWindowFlags(Qt.ToolTip | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.__loadUI()

        # Calculate the notification's position based on notification_count
        notification_height = self.height() + 10

        if self.parent.orientation == "top-right":
            notification_x = self.parent.screen.primaryScreen().size().width() - 20 - self.width()
            notification_y = 10 + notification_count * notification_height

        elif self.parent.orientation == "top-left":
            notification_x = 20
            notification_y = 10 + notification_count * notification_height

        elif self.parent.orientation == "bottom-right":
            notification_count += 1
            notification_x = self.parent.screen.primaryScreen().size().width() - 20 - self.width()
            notification_y = 10 + notification_count * notification_height
            notification_y = self.parent.screen.primaryScreen().size().height() - notification_y

        elif self.parent.orientation == "bottom-left":
            notification_count += 1
            notification_x = 20
            notification_y = 10 + notification_count * notification_height
            notification_y = self.parent.screen.primaryScreen().size().height() - notification_y

        elif self.parent.orientation == "center":
            notification_count += 1
            notification_x = (self.parent.screen.primaryScreen().size().width() - 250) / 2
            notification_y = (self.parent.screen.primaryScreen().size().height() - 320) / 2

        else:
            return

        self.enter_animation = QPropertyAnimation(self, b"pos")
        self.enter_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.enter_animation.setDuration(500)  # Animation duration in milliseconds

        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.opacity_animation.setDuration(1000)  # Animation duration in milliseconds

        self.disappear_animation = QPropertyAnimation(self, b"windowOpacity")
        self.disappear_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.disappear_animation.setStartValue(1.0)
        self.disappear_animation.setEndValue(0.0)
        self.disappear_animation.setDuration(5000)  # Animation duration in milliseconds

        self.show()

        start_notification_x = (
            self.parent.screen.primaryScreen().size().width()
            if "right" in self.parent.orientation
            else 0 - self.width()
        )

        self.move(start_notification_x, notification_y)
        self.enter_animation.setStartValue(QPoint(
            start_notification_x,
            notification_y
        ))

        self.enter_animation.setEndValue(QPoint(notification_x, notification_y))
        self.enter_animation.finished.connect(self.start_disappear_timer)
        self.enter_animation.start()
        self.opacity_animation.start()

        # Set up a timer to handle the disappearance animation
        self.disappearance_timer = QTimer(self)
        self.disappearance_timer.setInterval(self.parent.timelive * 1000)
        self.disappearance_timer.timeout.connect(self.close_notification)

    def start_delete(self, *_):
        self.moved = True
        if "disappearance_timer" in self.__dict__ and self.disappearance_timer and not self.disappearance_timer.isActive():
            self.disappearance_timer.start()

    def start_disappear_timer(self):
        # Start the timer to trigger the disappearance animation
        if self.moved:
            self.disappearance_timer.start()

    def mouseReleaseEvent(self, event):
        if self.parent.bind:
            self.parent.bind()

        self.close_notification(hand=True)

    def close_notification(self, hand=False, *args):
        if hand is False:
            self.disappear_animation.finished.connect(self.close)
            self.disappear_animation.finished.connect(self.deleteLater)
            self.disappear_animation.start()
        else:
            self.parent.notification_queue.clear()
            self.parent.delete_current_notification()
        self.finished.emit()
        if (
                "disappearance_timer" in self.__dict__
                and self.disappearance_timer
                and not self.disappearance_timer.isActive()
        ):
            self.disappearance_timer.stop()
            self.disappearance_timer.deleteLater()
            self.disappearance_timer = None
            self.parent.update_positions()

    def __loadUI(self):
        # self.setCursor(QCursor().shape().ForbiddenCursor)
        self.setObjectName("MessageBox")
        self.setStyleSheet("""
        QWidget#MessageBox, QTextEdit {
            background: #000;
            border: 1px solid white;
        }
        QPushButton {
            background: red;
        }
        * {
            color: white;
        }
        """)

        horizontal = QHBoxLayout(self)
        horizontal.setSpacing(10)
        horizontal.setContentsMargins(10, 10, 10, 10)

        # Create the vertical layout
        vertical_layout = QVBoxLayout()
        horizontal.addLayout(vertical_layout)

        # Create close button
        close_button = QPushButton(parent=self)
        close_button.clicked.connect(partial(self.close_notification, True))
        close_button.setFixedSize(15, 15)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Create the message_label
        message_label = QTextEdit(self.message, self)
        message_label.setFont(QFont("Inter", 10))
        message_label.setReadOnly(True)

        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        vertical_layout.addWidget(close_button, stretch=0, alignment=(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        ))
        vertical_layout.addWidget(message_label, stretch=0)


class NotificationManager(QWidget):
    def __init__(self, screen, orientation, bind=None, timelive=5):
        super().__init__()
        self.screen: QApplication = screen
        self.orientation = orientation
        self.timelive = timelive
        self.bind = bind

        if self.orientation not in ["top-right", "top-left", "bottom-right", "bottom-left", "center"]:
            raise ValueError("Нет такой ориетации уведомления.")

        self.counter = 0
        self.notification_queue = []

        self.notification_timer = QTimer(self)
        self.notification_timer.timeout.connect(self.show_queued_notification)
        self.notification_timer.start(1500)  # 1 second interval for checking notification queue

    def mouse_is_moved(self):
        for notification in self.findChildren(Notification):
            notification.start_delete()

    def delete_current_notification(self):
        for notification in self.findChildren(Notification):
            notification.close()
            notification.finished.emit()
            notification.deleteLater()

    def show_queued_notification(self):
        # Show a queued notification if there are less than 3 notifications displayed
        child = self.findChildren(Notification)
        if len(child) < 3 and self.notification_queue:
            title, message = self.notification_queue.pop(0)
            new_notification = Notification(title, message, self, len(self.findChildren(Notification)))
            new_notification.finished.connect(self.notification_closed)
            self.update_positions()
            return

    def notification_closed(self):
        # Remove closed notifications from the list
        self.update_positions(True)

    def update_positions(self, move=False):
        # Update the position of each notification based on the number of notifications
        notifications = self.findChildren(Notification)
        for idx, notification in enumerate(notifications):
            notification: Notification = notification

            notification_height = notification.height() + 10

            if self.orientation == "top-right":
                notification_x = self.screen.primaryScreen().size().width() - 20 - notification.width()
                notification_y = 10 + idx * (notification_height)

            elif self.orientation == "top-left":
                notification_x = 20
                notification_y = 10 + idx * (notification_height)

            elif self.orientation == "bottom-right":
                idx += 1
                notification_x = self.screen.primaryScreen().size().width() - 20 - notification.width()
                notification_y = 10 + idx * (notification_height)
                notification_y = self.screen.primaryScreen().size().height() - notification_y

            elif self.orientation == "bottom-left":
                idx += 1
                notification_x = 20
                notification_y = 10 + idx * (notification_height)
                notification_y = self.screen.primaryScreen().size().height() - notification_y
            else:
                return

            notification_x = int(notification_x / 10)
            notification_x = notification_x * 10

            notification_y = int(notification_y / 10)
            notification_y = notification_y * 10

            if move is True:
                current_position = notification.pos()
                move = QPropertyAnimation(notification, b"pos")
                move.setEasingCurve(QEasingCurve.InOutCubic)
                move.setDuration(100)  # Animation duration in milliseconds
                move.setStartValue(QPoint(current_position.x(), current_position.y()))
                move.setEndValue(QPoint(notification_x, notification_y))
                move.start()
            else:
                notification.move(notification_x, notification_y)

    def show_notification(self, title, message):
        # Add notification to the queue
        self.counter += 1
        self.notification_queue.append((title, message))

    def clear_queue(self):
        # Clear the notification queue
        self.notification_queue.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main = AutoTranslate(app)

    sys.exit(app.exec())
