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

import sys, time, uuid
#from PySide import QtGui, QtCore
from PySide.QtGui import *
from PySide import QtCore
from gevent import monkey; monkey.patch_all()

class Main(QWidget):

	icon_html = "<html><img src='images/{name}.png' width={side} height={side}></html>"
	
	def __init__(self, app):
		super(Main, self).__init__()
		
		self.app = app
		self.initUI()
		self.setupClip()
		
	def initUI(self):			   
		
		self.search = QLineEdit()
		
		self.list_widget  = QListWidget()
		list_widget_icon_size = QtCore.QSize(48,48)
		self.list_widget.setIconSize(list_widget_icon_size) #http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
		self.list_widget.setAlternatingRowColors(True) #http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors
		
		
		search_icon = QLabel(self.icon_html.format(name="find",side=32)) #http://www.iconarchive.com/show/super-mono-3d-icons-by-double-j-design/search-icon.html
		clipboard_icon = QLabel(self.icon_html.format(name="clipboard",side=32))

		grid =  QGridLayout(self) #passing QApplication instance will set the QGridLayout to it, or use #self.setLayout(grid)
		grid.setSpacing(10)
		
		grid.addWidget(self.search, 1 , 1)
		grid.addWidget(search_icon, 1 , 2)
		grid.addWidget(self.list_widget, 2 , 1)
		grid.addWidget(clipboard_icon, 2 , 2)
		
		#self.setLayout(grid)
		
		self.setGeometry(300, 300, 250, 150)
		self.setWindowTitle('PasteBeam 1.0.0')	
		
		self.show()
	
	def setupClip(self):
		self.clipboard = self.app.clipboard() #clipboard is in the QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
		self.clipboard.dataChanged.connect(self.onClipChange) #datachanged is signal, doclip is slot, so we are connecting slot to handle signal
		
	def onClipChange(self):
		#self.status.setText(self.clipboard.text() or str(self.clipboard.pixmap()) )
		pmap = self.clipboard.pixmap()
		if pmap:
			#crop and reduce pmap size to fit square icon
			w=pmap.width()
			h=pmap.height()
			is_square = w==h
			if not is_square:
				smallest_side = min(w, h)
				longest_side = max(w, h)
				shift = longest_side / 4.0
				is_landscape = w > h
				if is_landscape:
					x = shift
					y = 0
				else:
					x = 0
					y = shift
				pmap = pmap.copy(x, y, smallest_side, smallest_side) #PySide.QtGui.QPixmap.copy(x, y, width, height) #https://srinikom.github.io/pyside-docs/PySide/QtGui/QPixmap.html#PySide.QtGui.PySide.QtGui.QPixmap.copy
			pmap = pmap.scaled(48,48)
			itm =  QListWidgetItem()
			itm.setIcon(QIcon(pmap))
			txt = "Copied Image / Screenshot ({w} x {h})".format(w=w,h=h )
		else:
			itm = QListWidgetItem()
			itm.setIcon(QIcon("images/text.png"))
			txt = self.clipboard.text()
		self.list_widget.addItem(itm) #or self.list_widget.addItem("some text") (different signature)
		custom_label = QLabel("<html><b>By Test on {timestamp}:</b><pre>{text}</pre></html>".format(timestamp = time.time(), text=txt ) )
		self.list_widget.setItemWidget(itm, custom_label )
		itm.setSizeHint( custom_label.sizeHint() )
		#self.status.setText(str(time.time()))
		
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv) #create mainloop
	ex = Main(app) #run widgets
	sys.exit(app.exec_())