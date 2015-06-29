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
from PyQt5.QtWidgets import * #QWidget, QPushButton, QGridLayout, QApplication, QLineEdit
#from PyQt5.QtCore import QCoreApplication
#from PyQt5.QtMultimedia import QCamera, QMediaRecorder
#from PyQt5.QtMultimediaWidgets import QCameraViewfinder


class Example(QWidget):
	
	def __init__(self, app):
		super().__init__()
		
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

		grid =  QGridLayout()
		grid.setSpacing(10)
		
		grid.addWidget(cbtn, 1 , 1)
		grid.addWidget(self.status, 1 , 2)
		grid.addWidget(qbtn, 2 , 2)
		
		self.setLayout(grid)
		
		self.setGeometry(300, 300, 250, 150)
		self.setWindowTitle('Quit button')	
		self.show()
		
	def setupClip(self):
		self.clipboard = self.app.clipboard() #http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
		self.clipboard.dataChanged.connect(self.onClipChange) #datachanged is signal, doclip is slot
		
	def onClipChange(self):
		self.status.setText(self.clipboard.text() or str(self.clipboard.pixmap()) )
		#self.status.setText(str(time.time()))
		
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv) #create mainloop
	ex = Example(app) #run widgets
	sys.exit(app.exec_())