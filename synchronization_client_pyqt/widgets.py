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
		self.stacked_widget.switchToMainWidget()
		self.lockout_pin.clear()
		for each in self.menu_lockables:
			each.setEnabled(True)
		
	def onShowLockoutSlot(self):
		for each in self.menu_lockables:
			each.setEnabled(False)
		self.stacked_widget.switchToLockoutWidget()
		
class FaderWidget(QWidget):

	def __init__(self, old_widget, new_widget, duration = 333):
	
		QWidget.__init__(self, new_widget)
		
		self.old_pixmap = QPixmap(new_widget.size())
		old_widget.render(self.old_pixmap)
		self.pixmap_opacity = 1.0
		
		self.timeline = QtCore.QTimeLine()
		self.timeline.valueChanged.connect(self.animate)
		self.timeline.finished.connect(self.close)
		self.timeline.setDuration(duration)
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
		
class StackedWidgetFader(QStackedWidget):
	def __init__(self, parent):
		super(StackedWidgetFader, self).__init__(parent)
		self.duration = 444
	def setCurrentIndex(self, index):
		self.fader_widget = FaderWidget(self.currentWidget(), self.widget(index), self.duration) #does not work as a mixin, as self.currentWidget needs to be a subclass of QStackedWidget
		QStackedWidget.setCurrentIndex(self, index)
	def setFadeDuration(self, duration):
		self.duration = duration
		
class ListWidgetCommonsMixin(object):

	def doStyling(self, status="Double-click a clip to copy, or right-click for more options."):
		self.setIconSize(self.parent.icon_size) #http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
		self.setAlternatingRowColors(True) #http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors
		self.setStatusTip(status)


class StarListWidget(QListWidget, ListWidgetCommonsMixin):
	def __init__(self, parent = None):
		super(StarListWidget, self).__init__(parent)
		self.parent = parent
		self.doStyling()
		
class MainListWidget(QListWidget, ListWidgetCommonsMixin):
	def __init__(self, parent = None):
		super(MainListWidget, self).__init__(parent)
		self.parent = parent
		self.main = parent.main
		
		self.doStyling()
		self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
		#delete action
		delete_action = QAction(QIcon("images/close.png"), '&Delete', self) #delete.setText("Delete")
		delete_action.triggered.connect(self.onDeleteAction)
		self.addAction(delete_action)
		#star action
		star_action = QAction(QIcon("images/star.png"), '&Star', self)
		star_action.triggered.connect(self.onAddStarAction)
		self.addAction(star_action)
		
	
	def getClipDataByRow(self):
		current_row = self.currentRow()
		current_item = self.currentItem()
		current_item = json.loads(current_item.data(QtCore.Qt.UserRole))
		return current_row, current_item
	
	def onDeleteAction(self):
		current_row, current_item = self.getClipDataByRow()
		remove_id = current_item["_id"]
		async_process = dict(
			question = "Delete?",
			data = {"remove_id":remove_id, "remove_row":current_row}
		)
		self.main.outgoingSignalForWorker.emit(async_process)
		
	def onAddStarAction(self):
		current_row, current_item = self.getClipDataByRow()
		del current_item["_id"]
		async_process = dict(
			question = "Star?",
			data = current_item
		)
		self.main.outgoingSignalForWorker.emit(async_process)
		
	def onIncommingDelete(self,remove_row):
		self.takeItem(remove_row) #POSSIBLE RACE CONDITION
		
class FriendListWidget(QListWidget, ListWidgetCommonsMixin):
	def __init__(self, parent = None):
		super(FriendListWidget, self).__init__(parent)
		self.parent = parent
		self.doStyling()

class PanelStackedWidget(StackedWidgetFader):
	def __init__(self, icon_size, parent = None,):
		super(PanelStackedWidget, self).__init__(parent)
		self.main=parent
		self.icon_size=icon_size
		self.setFadeDuration(111)
		self.doPanels()
		self.addPanels()
	
	def doPanels(self):
			
		self.main_list_widget = MainListWidget(self)
		
		self.star_list_widget = StarListWidget(self)
		
		self.friend_list_widget = FriendListWidget(self)
				
		self.panels = [self.main_list_widget, self.star_list_widget, self.friend_list_widget]
		
		#self.list_widgets = [self.main_list_widget, self.star_list_widget.self.friends_list_widget] #friend_list_widget
	
	def addPanels(self):
		for each in self.panels:
			self.addWidget(each)
	
	def switchToDeviceListWidget(self):
		self.setCurrentIndex(0)
	
	def switchToStarListWidget(self):
		self.setCurrentIndex(1)

	def switchToFriendListWidget(self):
		self.setCurrentIndex(2)
		
class MainStackedWidget(StackedWidgetFader):
	#https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
	#http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
	def __init__(self, parent = None):
		#QStackedWidget.__init__(self, parent)
		super(MainStackedWidget, self).__init__(parent) # it's better to use super method instead of explicitly calling the parent class, because the former allows to add another parent and "push up" the previous parent up the ladder without making any changes to the code here
	
	def switchToMainWidget(self):
		self.setCurrentIndex(0)
	
	def switchToLockoutWidget(self):
		self.setCurrentIndex(1)