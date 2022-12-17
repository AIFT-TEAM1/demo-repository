import sys
from kiwoom.kiwoom import *
from PyQt5.QtWidgets import *

class ui_class():
    def __init__(self):

        self.app = QApplication(sys.argv)

        self.kiwoom = Kiwoom()

        self.app.exec_() #이벤트 루프 / 종료를 막아줌