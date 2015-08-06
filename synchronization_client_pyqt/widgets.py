import keyring

import bson.json_util as json

from PySide.QtGui import *

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