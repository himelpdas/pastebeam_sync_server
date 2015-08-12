import keyring

import bson.json_util as json

from PySide.QtGui import *
from PySide import QtCore

class AccountMixin(object):

	@staticmethod
	def getLogin():
		ring = keyring.get_password("pastebeam","account")
		login = json.loads(ring) if ring else {} #todo store email locally, and access only password!
		return login

	def showAccountDialogs(self):
		
		login = self.getLogin()
		
		email, e = QInputDialog.getText(self, 'Account', 
			'<html>Enter your <b>email</b>:</html>', 
			text = login.get("email"),
		)
		
		if not e:
			return
		
		password, p = QInputDialog.getText(self, 'Account', 
			'<html>Enter your <b>password</b>:</html>', 
			text = login.get("password"),
			echo=QLineEdit.Password
		)
		
		if not p:
			return
		
		keyring.set_password("pastebeam","account",json.dumps({
			"email":email, 
			"password":password,
		}))
		
		if hasattr(self, "ws_worker") and hasattr(self.ws_worker, "WSOCK"): #maybe not initialized yet
			self.ws_worker.WSOCK.close()
			self.ws_worker.KEEP_RUNNING = 1
			
class LockoutMixin(object):

	def initLockoutWidget(self):
		self.lockout_widget = QWidget()
		lockout_vbox = QVBoxLayout()
		lockout_hbox = QHBoxLayout()
		lockout_hbox.addStretch(1)
		self.lockout_pin = QLineEdit()
		self.lockout_pin.setAlignment(QtCore.Qt.AlignHCenter) #http://www.codeprogress.com/cpp/libraries/qt/QLineEditCenterText.php#.VcnX9M7RtyN
		#self.lockout_pin.setValidator(QIntValidator(0, 9999)) #OLD# http://doc.qt.io/qt-4.8/qlineedit.html#inputMask-prop 
		#self.lockout_pin.setMaxLength(4) #still need it despite setValidator or else you can keep typing
		self.lockout_pin.setEchoMode(QLineEdit.Password) #hide with bullets #http://stackoverflow.com/questions/4663207/masking-qlineedit-text
		self.lockout_pin.setStatusTip("Type your account password to unlock.")
		
		self.lockout_pin.textEdited.connect(self.onLockoutPinTypedSlot)
		
		lockout_hbox.addWidget(self.lockout_pin)
		lockout_hbox.addStretch(1)
		lockout_vbox.addLayout(lockout_hbox)
		self.lockout_widget.setLayout(lockout_vbox)
		#self.lockout_widget.hide()
		self.stacked_widget.addWidget(self.lockout_widget)
		
	def onLockoutPinTypedSlot(self, written):
		login = self.getLogin().get("password")
		if not login:
			pass #no password was set yet
		elif login != written:
			return
		self.stacked_widget.setMainWidget()
		self.lockout_pin.clear()
		
	def onShowLockoutSlot(self):
		self.stacked_widget.setLockoutWidget()
		
class FaderWidget(QWidget):

	def __init__(self, old_widget, new_widget):
	
		QWidget.__init__(self, new_widget)
		
		self.old_pixmap = QPixmap(new_widget.size())
		old_widget.render(self.old_pixmap)
		self.pixmap_opacity = 1.0
		
		self.timeline = QtCore.QTimeLine()
		self.timeline.valueChanged.connect(self.animate)
		self.timeline.finished.connect(self.close)
		self.timeline.setDuration(333)
		self.timeline.start()
		
		self.resize(new_widget.size())
		self.show()
	
	def paintEvent(self, event):
	
		painter = QPainter()
		painter.begin(self)
		painter.setOpacity(self.pixmap_opacity)
		painter.drawPixmap(0, 0, self.old_pixmap)
		painter.end()
	
	def animate(self, value):
	
		self.pixmap_opacity = 1.0 - value
		self.repaint()

		
		
class StackedWidget(QStackedWidget):
	#https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
	#http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
	def __init__(self, parent = None):
		QStackedWidget.__init__(self, parent)
	
	def setCurrentIndex(self, index):
		self.fader_widget = FaderWidget(self.currentWidget(), self.widget(index))
		QStackedWidget.setCurrentIndex(self, index)
	
	def setMainWidget(self):
		self.setCurrentIndex(0)
	
	def setLockoutWidget(self):
		self.setCurrentIndex(1)