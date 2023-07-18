import re
import math
import sys
import qdarktheme
from pathlib import Path
from PySide6.QtGui import QKeyEvent, QIcon
from PySide6.QtWidgets import (
    QLineEdit, QPushButton, QGridLayout,
    QLabel, QWidget, QVBoxLayout, QMessageBox, QMainWindow, QApplication)
from PySide6.QtCore import Qt, Signal, Slot


NUM_OR_DOT_REGEX = re.compile(r'^[0-9.]$')
ROOT_DIR = Path(__file__).parent
FILES_DIR = ROOT_DIR / 'files'
WINDOW_ICON_PATH = FILES_DIR / 'icon.png'

# Colors
PRIMARY_COLOR = '#1e81b0'
DARKER_PRIMARY_COLOR = '#16658a'
DARKEST_PRIMARY_COLOR = '#115270'

# Sizing
BIG_FONT_SIZE = 40
MEDIUM_FONT_SIZE = 24
SMALL_FONT_SIZE = 18
TEXT_MARGIN = 15
MINIMUM_WIDTH = 500

qss = f"""
    QPushButton[cssClass="specialButton"] {{
        color: #fff;
        background: {PRIMARY_COLOR};
    }}
    QPushButton[cssClass="specialButton"]:hover {{
        color: #fff;
        background: {DARKER_PRIMARY_COLOR};
    }}
    QPushButton[cssClass="specialButton"]:pressed {{
        color: #fff;
        background: {DARKEST_PRIMARY_COLOR};
    }}
"""


def setupTheme():
    qdarktheme.setup_theme(
        theme='dark',
        corner_shape='rounded',
        custom_colors={
            "[dark]": {
                "primary": f"{PRIMARY_COLOR}",
            },
            "[light]": {
                "primary": f"{PRIMARY_COLOR}",
            },
        },
        additional_qss=qss
    )


def isNumOrDot(string: str):
    return bool(NUM_OR_DOT_REGEX.search(string))


def convertToNumber(string: str):
    number = float(string)
    if number.is_integer():
        number = int(number)
    return number


def isValidNumber(string: str):
    try:
        float(string)
        valid = True
    except ValueError:
        valid = False
    return valid


def isEmpty(string: str):
    return len(string) == 0


class MainWindow(QMainWindow):

    def __init__(self, parent: QWidget | None = None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.central_widget = QWidget()
        self.vLayout = QVBoxLayout()
        self.central_widget.setLayout(self.vLayout)
        self.setCentralWidget(self.central_widget)
        self.setWindowTitle('Calculadora')

    def adjustFixedSize(self):
        self.adjustSize()
        self.setFixedSize(self.width(), self.height())

    def addWidgetToVLayout(self, widget: QWidget):
        self.vLayout.addWidget(widget)

    def makeMsgBox(self):
        return QMessageBox(self)


class Display(QLineEdit):
    eqPressed = Signal()
    delPressed = Signal()
    clearPressed = Signal()
    inputPressed = Signal(str)
    operatorPressed = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configStyle()

    def _configStyle(self):
        margins = [TEXT_MARGIN for _ in range(4)]
        self.setStyleSheet(f'font-size: {BIG_FONT_SIZE}px;')
        self.setMinimumHeight(BIG_FONT_SIZE * 2)
        self.setMinimumWidth(MINIMUM_WIDTH)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setTextMargins(*margins)

    def keyPressEvent(self, arg__1: QKeyEvent) -> None:
        text = arg__1.text().strip()
        key = arg__1.key()
        KEYS = Qt.Key
        isEnter = key in [KEYS.Key_Enter, KEYS.Key_Return, KEYS.Key_Equal]
        isDelete = key in [KEYS.Key_Backspace, KEYS.Key_Delete, KEYS.Key_D]
        isEsc = key in [KEYS.Key_Escape, KEYS.Key_C]
        isOperator = key in [KEYS.Key_Plus, KEYS.Key_Minus,
                             KEYS.Key_Slash, KEYS.Key_Asterisk, KEYS.Key_P]

        if isEnter:
            self.eqPressed.emit()
            return arg__1.ignore()

        if isDelete:
            self.delPressed.emit()
            return arg__1.ignore()

        if isEsc:
            self.clearPressed.emit()
            return arg__1.ignore()

        if isOperator:
            if text.lower() == 'p':
                text = '^'
            self.operatorPressed.emit(text)
            return arg__1.ignore()
        # Não passar daqui se não tiver texto
        if isEmpty(text):
            return arg__1.ignore()

        if isNumOrDot(text):

            self.inputPressed.emit(text)
            return arg__1.ignore()


class Button(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configStyle()

    def configStyle(self):
        font = self.font()
        font.setPixelSize(MEDIUM_FONT_SIZE)
        self.setFont(font)
        self.setMinimumSize(75, 75)


class ButtonsGrid(QGridLayout):
    def __init__(
        self, display: 'Display', info: 'Info', window: 'MainWindow',
            *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._gridMask = [
            ['C', '◀', '^', '/'],
            ['7', '8', '9', '*'],
            ['4', '5', '6', '-'],
            ['1', '2', '3', '+'],
            ['N',  '0', '.', '='],
        ]
        self.display = display
        self.info = info
        self.window = window
        self._equation = ''
        self._equationInicialValue = 'Sua Conta'
        self._left = None
        self._right = None
        self._op = None

        self.equation = self._equationInicialValue
        self._makeGrid()

    @property
    def equation(self):
        return self._equation

    @equation.setter
    def equation(self, value):

        self._equation = value
        self.info.setText(value)

    def _makeGrid(self):
        self.display.eqPressed.connect(self._eq)
        self.display.delPressed.connect(self._backspace)
        self.display.clearPressed.connect(self._clear)
        self.display.inputPressed.connect(self._insertToDisplay)
        self.display.operatorPressed.connect(self._configLeftOp)

        for rowNumber, rowData in enumerate(self._gridMask):
            for columNumber, buttonText in enumerate(rowData):
                button = Button(buttonText)

                if not isNumOrDot(buttonText) and not isEmpty(buttonText):
                    button.setProperty('cssClass', 'specialButton')
                    self._configSpecialButton(button)
                self.addWidget(button, rowNumber, columNumber)
                slot = self._makeSlot(
                    self._insertToDisplay,
                    buttonText)
                self._connectButtonClicked(button, slot)

    def _connectButtonClicked(self, button, slot):
        button.clicked.connect(slot)

    def _configSpecialButton(self, button):
        text = button.text()

        if text == 'C':
            self._connectButtonClicked(button, self._clear)
        if text == '◀':
            self._connectButtonClicked(button, self.display.backspace)
        if text == 'N':
            self._connectButtonClicked(button, self._invertNumber)
        if text in '+-*/^':
            self._connectButtonClicked(
                button,
                self._makeSlot(self._configLeftOp, text)
            )
        if text == '=':
            self._connectButtonClicked(
                button, self._eq)

    @Slot()
    def _makeSlot(self, func, *args, **kwargs):
        @Slot(bool)
        def realSlot(_):
            func(*args, **kwargs)
        return realSlot

    @Slot()
    def _invertNumber(self):
        displayText = self.display.text()
        if not isValidNumber(displayText):
            return
        number = convertToNumber(displayText) * -1
        self.display.setText(str(number))

    @Slot()
    def _insertToDisplay(self, text):
        buttonText = text
        newDisplayValue = self.display.text() + text

        if not isValidNumber(newDisplayValue):
            self.display.setFocus()
            return
        self.display.insert(buttonText)
        self.display.setFocus()

    @Slot()
    def _clear(self):
        self._left = None
        self._right = None
        self._op = None
        self.equation = self._equationInicialValue
        self.display.clear()
        self.display.setFocus()

    @Slot()
    def _configLeftOp(self, text):

        displayText = self.display.text()
        self.display.clear()
        if not isValidNumber(displayText) and self._left is None:
            self._showError('Você não digitou nada')
            return

        if self._left is None:
            self._left = convertToNumber(displayText)
        self._op = text
        self.equation = f'{self._left} {self._op} ??'
        self.display.setFocus()

    @Slot()
    def _eq(self):
        displayText = self.display.text()

        if not isValidNumber(displayText) or self._left is None:
            self._showError('Conta incompleta')
            self.display.setFocus()
            return
        self._right = convertToNumber(displayText)
        self.equation = f'{self._left} {self._op} {self._right}'
        result = 'error'
        try:
            if '^' in self.equation and isinstance(self._left, float | int):
                result = math.pow(self._left, self._right)
                result = convertToNumber(str(result))
            else:
                result = eval(self.equation)
        except ZeroDivisionError:
            self._showError('Você tentou dividir por zero')

        except OverflowError:
            self._showError('Número muito grande')

        self.display.clear()
        self.info.setText(f'{self.equation} = {result}')
        self._left = result
        self._right = None
        self.display.setFocus()
        if result == 'error':
            self._left = None

    def _backspace(self):
        self.display.backspace()
        self.display.setFocus()

    def _makeDialog(self, text):
        msgBox = self.window.makeMsgBox()
        msgBox.setText(text)
        return msgBox

    def _showError(self, text):
        msgBox = self._makeDialog(text)
        msgBox.setIcon(msgBox.Icon.Critical)
        msgBox.exec()
        self.display.setFocus()

    def _showInfo(self, text):
        msgBox = self._makeDialog(text)
        msgBox.setIcon(msgBox.Icon.Information)
        msgBox.exec()


class Info(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.configStyle()

    def configStyle(self):
        self.setStyleSheet(f'font-size: {SMALL_FONT_SIZE}px;')
        self.setAlignment(Qt.AlignmentFlag.AlignRight)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    setupTheme()
    window = MainWindow()

    icon = QIcon(str(WINDOW_ICON_PATH))
    window.setWindowIcon(icon)
    app.setWindowIcon(icon)

    info = Info('Sua Conta')
    window.addWidgetToVLayout(info)

    display = Display()
    window.addWidgetToVLayout(display)

    buttonsGrid = ButtonsGrid(display, info, window)
    window.vLayout.addLayout(buttonsGrid)

    window.adjustFixedSize()
    window.show()
    app.exec()
