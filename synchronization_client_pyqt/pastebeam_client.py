#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
ZetCode PyQt5 tutorial 

This program creates a quit
button. When we press the button,
the application terminates. 

author: Jan Bodnar
website: zetcode.com 
last edited: January 2015
"""

import sys, time
#from PySide import QtGui, QtCore
from PySide.QtGui import *
from gevent import monkey; monkey.patch_all()

class Main(QWidget):
	
	def __init__(self, app):
		super(Main, self).__init__()
		
		self.app = app
		self.initUI()
		self.setupClip()
		
	def initUI(self):			   
		
		qbtn = QPushButton('Quit')
		qbtn.clicked.connect(self.app.quit)
		qbtn.resize(qbtn.sizeHint()) #probably sets size to width of "Quit" text
		#qbtn.move(50, 50)	
				
		cbtn = QPushButton('Clip')
		cbtn.resize(cbtn.sizeHint()) #probably sets size to width of "Quit" text
		#qbtn.move(50, 50)	
		
		self.status = QLineEdit()
		
		self.listview  = QListWidget()

		grid =  QGridLayout()
		grid.setSpacing(10)
		
		grid.addWidget(cbtn, 1 , 1)
		grid.addWidget(self.status, 1 , 2)
		grid.addWidget(qbtn, 2 , 2)
		grid.addWidget(self.listview, 3 , 1)
		
		self.setLayout(grid)
		
		self.setGeometry(300, 300, 250, 150)
		self.setWindowTitle('Quit button')	
		self.show()
		
	def setupClip(self):
		self.clipboard = self.app.clipboard() #clipboard is in the QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
		self.clipboard.dataChanged.connect(self.onClipChange) #datachanged is signal, doclip is slot
		
	def onClipChange(self):
		self.status.setText(self.clipboard.text() or str(self.clipboard.pixmap()) )
		#self.status.setText(str(time.time()))
		
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv) #create mainloop
	ex = Main(app) #run widgets
	sys.exit(app.exec_())