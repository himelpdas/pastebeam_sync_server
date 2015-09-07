import keyring

import bson.json_util as json

from functions import *

from PySide.QtGui import *
from PySide import QtCore
"""
class AccountMixin(object):

	@staticmethod
	def getLogin():
		ring = keyring.get_password("pastebeam","account")
		login = json.loads(ring) if ring else {} #todo store email locally, and access only password!
		return login

	def showAccountDialogs(self):
		
		login = self.getLogin()
		
		email, e = QInputDialog.getText(self, 'Account', 
			'Enter your <b>email</b>:', 
			text = login.get("email"),
		)
		
		if not e:
			return
		
		password, p = QInputDialog.getText(self, 'Account', 
			'Enter your <b>password</b>:', 
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
"""
			
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
		
class OkCancelWidgetMixin(object):
	def doOkCancelWidget(self):
		ok_button = QPushButton("Ok")
		ok_button.clicked.connect(self.onOkButtonClickedSlot)
		cancel_button = QPushButton("Cancel")
		cancel_button.clicked.connect(self.onCancelButtonClickedSlot)
		okcancel_hbox = QHBoxLayout()
		okcancel_hbox.addStretch(1)
		okcancel_hbox.addWidget(ok_button)
		okcancel_hbox.addWidget(cancel_button)
		self.okcancel_widget = QWidget()
		self.okcancel_widget.setLayout(okcancel_hbox)
		
	def onOkButtonClickedSlot(self):
		self.done(1)
			
	def onCancelButtonClickedSlot(self):
		
		self.done(0)

		
class SettingsDialog(QDialog, OkCancelWidgetMixin): #http://www.qtcentre.org/threads/37058-modal-QWidget

	@classmethod
	def show(cls, parent):
		cls(parent)
	
	def __init__(self, parent = None, f = 0):
		super(self.__class__, self).__init__()
		self.main = parent
		self.current_login = self.main.getLogin()
		self.setWindowTitle("Edit Settings")
		self.doAccountWidget()
		self.doSystemWidget()
		self.doStartupWidget()
		self.doTabWidget()
		self.doOkCancelWidget()
		self.doSettingsLayout()
		self.setLayout(self.settings_layout)
		self.exec_()
		
	def doAccountWidget(self):		
		email_hbox = QHBoxLayout()
		email_label = QLabel("Email:")
		self.email_line = QLineEdit(self.current_login.get("email"))
		email_hbox.addWidget(email_label)
		email_hbox.addWidget(self.email_line)
		email_widget = QWidget()
		email_widget.setLayout(email_hbox)
		
		password_hbox = QHBoxLayout()
		password_label = QLabel("Password:")
		self.password_line = QLineEdit(self.current_login.get("password"))
		self.password_line.setEchoMode(QLineEdit.Password)
		password_hbox.addWidget(password_label)
		password_hbox.addWidget(self.password_line)
		password_widget = QWidget()
		password_widget.setLayout(password_hbox)
		
		register_link = QLabel("<a href='#'>Register</a>")
		seperator = QLabel("|")
		forgot_link = QLabel("<a href='#'>Forgot password?</a>")
		links_hbox = QHBoxLayout()
		links_hbox.addWidget(register_link)
		links_hbox.addWidget(seperator)
		links_hbox.addWidget(forgot_link)
		links_hbox.setAlignment(QtCore.Qt.AlignRight)
		links_widget = QWidget()
		links_widget.setLayout(links_hbox)
		
		account_vbox = QVBoxLayout()
		account_vbox.addWidget(email_widget)
		account_vbox.addWidget(password_widget)
		account_vbox.addWidget(links_widget)
		
		self.account_widget = QWidget()		
		self.account_widget.setLayout(account_vbox)
		
	def doSystemWidget(self):
		device_name_label = QLabel("Device Name:")
		device_name_line = QLineEdit()
		device_name_hbox = QHBoxLayout()
		device_name_hbox.addWidget(device_name_label)
		device_name_hbox.addWidget(device_name_line)
		device_name_widget = QWidget()
		device_name_widget.setLayout(device_name_hbox)
		
		sync_label = QLabel("Automatically check for updates")
		sync_check = QCheckBox()
		sync_hbox  = QHBoxLayout()
		sync_hbox.addWidget(sync_label)
		sync_hbox.addWidget(sync_check)
		sync_widget = QWidget()
		sync_widget.setLayout(sync_hbox)
		
		master_vbox = QVBoxLayout()
		master_vbox.addWidget(device_name_widget)
		master_vbox.addWidget(sync_widget)
		
		self.system_widget = QWidget()
		self.system_widget.setLayout(master_vbox)
		
	def doStartupWidget(self):
		
		run_label = QLabel("Run PasteBeam")
		run_check = QCheckBox()
		run_hbox = QHBoxLayout()
		run_hbox.addWidget(run_label)
		run_hbox.addWidget(run_check)
		run_widget = QWidget()
		run_widget.setLayout(run_hbox)
		
		updates_label = QLabel("Check for updates")
		updates_check = QCheckBox()
		updates_hbox = QHBoxLayout()
		updates_hbox.addWidget(updates_label)
		updates_hbox.addWidget(updates_check)
		updates_widget = QWidget()
		updates_widget.setLayout(updates_hbox)		
		
		self.startup_layout = QVBoxLayout()
		self.startup_layout.addWidget(run_widget)
		self.startup_layout.addWidget(updates_widget)
		
		self.startup_widget = QWidget()
		self.startup_widget.setLayout(self.startup_layout)
		
	def doTabWidget(self):
		self.tab_widget = QTabWidget()
		self.tab_widget.addTab(self.account_widget, QIcon("images/account"), "Account")
		self.tab_widget.addTab(self.system_widget, QIcon("images/system"), "System")
		self.tab_widget.addTab(self.startup_widget, QIcon("images/controls"), "Startup")
	
	def doSettingsLayout(self):
		self.settings_layout = QVBoxLayout()
		self.settings_layout.addWidget(self.tab_widget)
		self.settings_layout.addWidget(self.okcancel_widget)
		
	def onOkButtonClickedSlot(self):
		self.setAccountInfoToKeyring()
		self.done(1)
			
	def onCancelButtonClickedSlot(self):
		
		self.done(0)

	def setAccountInfoToKeyring(self):
		
		login = self.main.getLogin()
		
		typed_email = self.email_line.text()
		typed_password = self.password_line.text()
		
		if not typed_email and typed_password: #TODO STRONGER VALIDATION HERE
			return
		
		keyring.set_password("pastebeam","account",json.dumps({
			"email":typed_email, 
			"password":typed_password,
		}))
		
		if hasattr(self.main, "ws_worker") and hasattr(self.main.ws_worker, "WSOCK"): #maybe not initialized yet
			if self.main.ws_worker.WSOCK:
				self.main.ws_worker.WSOCK.close()
			self.main.ws_worker.KEEP_RUNNING = 1
			
class ContactsDialog(QDialog, OkCancelWidgetMixin):
	
	@classmethod
	def show(cls, parent):
		cls(parent)
	
	def __init__(self, parent):
		super(self.__class__, self).__init__(parent)
		self.main = parent
		self.added_contacts_list = []
		self.setWindowTitle('Edit Contacts')
		self.doAddContactWidget()
		self.doListWidget()
		self.doOkCancelWidget()
		self.doContactsWidget()
		self.setLayout(self.contacts_layout)
		self.resizeMinWindowSizeForListWidget()
		self.exec_()
		
	def onAddButtonClickSlot(self):
		email = self.email_line.text()
		if not email or not validators.email(email):
			#show error
			return
		nickname  = self.nickname_line.text()
		if nickname:
			view = "{nickname} <{email}>".format(email=email,nickname=nickname)
		else:
			view = email

		#view = "<b>%s</b>"%view #make it bold to differentate from the ones already there.
		self.added_contacts_list.append(view)
		self.contacts_list.addItem(view)
	
	def onOkButtonClickedSlot(self):
		self.main.panel_stacked_widget.main_list_widget.contacts_list.extend(self.added_contacts_list)
		self.main.panel_stacked_widget.main_list_widget.doShareSubActions()
		super(self.__class__,self).onOkButtonClickedSlot()
	
	def resizeMinWindowSizeForListWidget(self):
		default_height = self.sizeHint().height()
		new_height = default_height *1.15
		self.setMinimumHeight(new_height)
		
	def doAddContactWidget(self):	
		email_label = QLabel("Friend's<br>Email:")
		self.email_line = email_line = QLineEdit()
		email_hbox = QHBoxLayout()
		email_hbox.addWidget(email_label)
		email_hbox.addWidget(email_line)
		email_widget = QWidget()
		email_widget.setLayout(email_hbox)
		
		nickname_label = QLabel("Nickname<br>(Optional):")
		self.nickname_line = nickname_line = QLineEdit()
		nickname_hbox = QHBoxLayout()
		nickname_hbox.addWidget(nickname_label)
		nickname_hbox.addWidget(nickname_line)
		nickname_widget = QWidget()
		nickname_widget.setLayout(nickname_hbox)

		lines_vbox = QVBoxLayout()
		lines_vbox.addWidget(email_widget)
		lines_vbox.addWidget(nickname_widget)
		lines_widget = QWidget()
		lines_widget.setLayout(lines_vbox)
		
		add_button = QPushButton("Add Friend")
		add_button.clicked.connect(self.onAddButtonClickSlot)
		add_user_hbox = QHBoxLayout()
		add_user_hbox.addWidget(lines_widget)
		add_user_hbox.addWidget(add_button)
		self.add_user_widget = QWidget()
		self.add_user_widget.setLayout(add_user_hbox)		
		
	def doListWidget(self):
		contacts_list_label = QLabel("Contact list:")
		self.contacts_list = QListWidget()
		#for letter in range(65,91):
		#	self.contacts_list.addItem("%s@yahoo.com"%chr(letter))
		contacts_list_delete = QPushButton("Delete")
		contacts_list_layout = QVBoxLayout()
		contacts_list_layout.addWidget(contacts_list_label)
		contacts_list_layout.addWidget(self.contacts_list)
		contacts_list_layout.addWidget(contacts_list_delete)
		self.contacts_list_widget = QListWidget()
		self.contacts_list_widget.setLayout(contacts_list_layout)
		
	def doContactsWidget(self):
		#how_label = QLabel("For your security, clips from other PasteBeam users are automatically blocked without notice. To unblock a friend, add his email to your contacts list here. Likewise, for him to receive your clips, he must add your login email to his own contacts list.")
		#how_label.setWordWrap(True)
		
		self.contacts_layout = QVBoxLayout()
		#self.contacts_layout.addWidget(how_label)
		self.contacts_layout.addWidget(self.add_user_widget)
		self.contacts_layout.addWidget(self.contacts_list_widget)
		self.contacts_layout.addWidget(self.okcancel_widget)
				
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
		
class CommonListWidget(QListWidget):
	def __init__(self, parent = None):
		super(CommonListWidget, self).__init__(parent)
		self.contacts_list = []
		self.parent = parent
		self.main = parent.main
		self.doStyling()
		#delete action
		self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
		
		self.doCopyAction()
		
		self.doShareAction()
		
		self.doUncommon() #do uncommon here
		
		self.doDeleteAction() #Put delete last

	def doStyling(self, status="Double-click an item to copy it, or right-click it for more options."):
		self.setIconSize(self.parent.icon_size) #http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
		self.setAlternatingRowColors(True) #http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors
		self.setStatusTip(status)
		
	def doShareAction(self):
		self.share_action = QAction(QIcon("images/share.png"), "S&hare", self)
		self.addAction(self.share_action)
	
	def doCopyAction(self):
		copy_action = QAction(QIcon("images/copy.png"), "&Copy", self)
		copy_action.triggered.connect(self.onCopyActionSlot)
		self.addAction(copy_action)
		separator = QAction(self)
		separator.setSeparator(True)
		self.addAction(separator)
	
	def doDeleteAction(self):
		separator = QAction(self)
		separator.setSeparator(True) #http://www.qtcentre.org/threads/21838-Separator-in-context-menu
		delete_action = QAction(QIcon("images/trash.png"), '&Delete', self) #delete.setText("Delete")
		delete_action.triggered.connect(self.onDeleteAction)
		self.addAction(separator)
		self.addAction(delete_action)
		
	def onDeleteAction(self):
		current_row, current_item = self.getClipDataByRow()
		remove_id = current_item["_id"]
		async_process = dict(
			question = "Delete?",
			data = {"remove_id":remove_id, "remove_row":current_row, "list_widget_name":self.__class__.__name__}
		)
		self.main.outgoingSignalForWorker.emit(async_process)
		
	def getClipDataByRow(self):
		current_row = self.currentRow()
		current_item = self.currentItem()
		current_item = json.loads(current_item.data(QtCore.Qt.UserRole)) #http://stackoverflow.com/questions/25452125/is-it-possible-to-add-a-hidden-value-to-every-item-of-qlistwidget
		return current_row, current_item
		
	def onCopyActionSlot(self):
		self.onItemDoubleClickSlot(self.currentItem())
		
	def onItemDoubleClickSlot(self, double_clicked_item):
		
		#current_item = self.item(0)
		#current_clip = json.loads(current_item.data(QtCore.Qt.UserRole))
		
		double_clicked_clip = json.loads(double_clicked_item.data(QtCore.Qt.UserRole)) 
		
		hash, prev = double_clicked_clip["hash"], self.main.previous_hash
		
		if hash == prev:
			self.main.onSetStatusSlot(("already copied","warn"))
			return
			
		#container name is already in double_clicked_clip
			
		#convert back to device clip
		del double_clicked_clip["_id"] #this is an id from an old clip from server. must remove or else key error will occur on server when trying to insert new clip 
		double_clicked_clip.pop("starred", None) 
		double_clicked_clip.pop("friend", None) 
		
		self.main.onSetNewClipSlot(double_clicked_clip)
		
		#self.previous_hash = hash #or else onClipChangeSlot will react and a duplicate new list item will occur.

class StarListWidget(CommonListWidget):
	def doUncommon(self):
		pass
		
class MainListWidget(CommonListWidget):
	def doUncommon(self):
		self.doStarAction()
		self.doShareSubActions()
		
	def doShareSubActions(self):
		if not self.contacts_list:
			self.share_action.setDisabled(True)
			#ADD bubble explainin why
		else:
			self.share_action.setDisabled(False)
		share_menu = QMenu()
		for name in self.contacts_list:
			friend = QAction(name, self)
			share_menu.addAction(name)
			self.share_action.setMenu(share_menu)

	def doStarAction(self):
		#star action
		star_action = QAction(QIcon("images/star.png"), '&Star', self)
		star_action.triggered.connect(self.onAddStarAction)
		self.addAction(star_action)
		
	def onAddStarAction(self):
		current_row, current_item = self.getClipDataByRow()
		del current_item["_id"]
		async_process = dict(
			question = "Star?",
			data = current_item
		)
		self.main.outgoingSignalForWorker.emit(async_process)
		
class FriendListWidget(CommonListWidget):
	def doUncommon(self):
		pass

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
		
	def onIncommingDelete(self,location):
		list_widget_name, remove_row = location
		
		if list_widget_name == "MainListWidget":
			self.main_list_widget.takeItem(remove_row) #POSSIBLE RACE CONDITION
		elif list_widget_name == "StarListWidget":
			self.star_list_widget.takeItem(remove_row)
		elif list_widget_name == "FriendListWidget":
			self.friend_list_widget.takeItem(remove_row)
			
	def clearAllLists(self):
		for each in self.panels:
			each.clear()
		
	def getMatchingContainerForHash(self, hash):
		hash_to_container = {}
		for list_widget in self.panels:
			row = 0
			while row < list_widget.count(): #http://www.qtcentre.org/threads/32716-How-to-iterate-through-QListWidget-items
				each_item = list_widget.item(row)
				item_data = each_item.data(QtCore.Qt.UserRole)
				json_data = json.loads(item_data)
				hash_container_pair = {json_data["hash"] : json_data["container_name"]}
				hash_to_container.update(hash_container_pair)
				row+=1
			
		container = hash_to_container.get(hash) #or None
		del hash_to_container
		return container
		
class LockoutStackedWidget(StackedWidgetFader):
	#https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
	#http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
	def __init__(self, parent = None):
		#QStackedWidget.__init__(self, parent)
		super(LockoutStackedWidget, self).__init__(parent) # it's better to use super method instead of explicitly calling the parent class, because the former allows to add another parent and "push up" the previous parent up the ladder without making any changes to the code here
	
	def switchToMainWidget(self):
		self.setCurrentIndex(0)
	
	def switchToLockoutWidget(self):
		self.setCurrentIndex(1)
