#from PySide import QtGui, QtCore
from PySide.QtGui import *
from PySide import QtCore, QtGui

class LoginDialog(Qwidget):
	def __init__(self):
		super(LoginDialog, self).__init__()
	def setupInterface():
		self.hbox = QHBoxLayout()
		
		self.username_label = QLabel("Username:")
		self.username_line = QLineEdit()
		
		hbox.addWidget(username_label)
		hbox.addWidget(username_line)
		self.setLayout(hbox)