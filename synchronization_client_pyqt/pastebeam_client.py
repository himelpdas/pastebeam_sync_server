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

import sys
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtMultimedia import QCamera, QMediaRecorder
from PyQt5.QtMultimediaWidgets import QCameraViewfinder


class Example(QWidget):
	
	def __init__(self):
		super().__init__()
		
		self.initUI()
		self.initCam()
	
	def initCam(self):
		#http://stackoverflow.com/questions/17650710/recording-video-from-usb-cam-with-qt5
		camera = QCamera(self)
		viewFinder = QCameraViewfinder(self)
		camera.setViewfinder(viewFinder)
		recorder = QMediaRecorder(camera,self)
		camera.setCaptureMode(QCamera.CaptureVideo);
		camera.start()
		viewFinder.show()
		
	def initUI(self):			   
		
		qbtn = QPushButton('Quit', self)
		qbtn.clicked.connect(QCoreApplication.instance().quit)
		qbtn.resize(qbtn.sizeHint())
		qbtn.move(50, 50)	   
		
		self.setGeometry(300, 300, 250, 150)
		self.setWindowTitle('Quit button')	
		self.show()
		
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv)
	ex = Example()
	sys.exit(app.exec_())