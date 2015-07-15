# coding=utf8

import gevent
from gevent.event import AsyncResult

#from gevent.queue import Queue #CANNOT USE QUEUE BECAUSE GEVENT CANNOT SWITCH CONTEXTS BETWEEN THREADS

from functions import *



from ws4py.client.geventclient import WebSocketClient
from PySide.QtGui import *
from PySide import QtCore

import encompress

DEFAULT_DOMAIN = "192.168.0.191"
DEFAULT_PORT = 8084

class WebsocketWorkerMixin(object):

	outgoingSignalForWorker = QtCore.Signal(dict)	
	
	def onIncommingSlot(self, emitted):
		#print emitted #display clips here
		#print "\n\n"+type(emitted)
		if emitted["clip_type"] == "screenshot":
			#crop and reduce pmap size to fit square icon
			itm =  QListWidgetItem()
			image = QImage()
			#print "\n\n\n"
			print image.loadFromData(emitted["clip_display"]["thumb"])
			itm.setIcon(QIcon(QPixmap(image)))
			txt = emitted["clip_display"]["text"]
		self.list_widget.addItem(itm) #or self.list_widget.addItem("some text") (different signature)
		custom_label = QLabel("<html><b>By Test on {timestamp}:</b><pre>{text}</pre></html>".format(timestamp = time.time(), text=txt ) )
		self.list_widget.setItemWidget(itm, custom_label )
		itm.setSizeHint( custom_label.sizeHint() )
			
class WebsocketWorker(QtCore.QThread):

	#This is the signal that will be emitted during the processing.
	#By including int as an argument, it lets the signal know to expect
	#an integer argument when emitting.
	incommingSignalForMain = QtCore.Signal(dict)

	#You can do any extra things in this init you need, but for this example
	#nothing else needs to be done expect call the super's init
	def __init__(self, main):
		QtCore.QThread.__init__(self)
				
		self.main = main
		self.temp_dir = self.main.temp_dir
		self.main.outgoingSignalForWorker.connect(self.onOutgoingSlot) #we have to use slots as gevent cannot talk to separate threads that weren't monkey_patched (QThreads are not monkey_patched since they are not pure python)
		
		self.OUTGOING_QUEUE = deque() #must use alternative Queue for non standard library thread and greenlets
		
	#A QThread is run by calling it's start() function, which calls this run()
	#function in it's own "thread". 
	
	def onOutgoingSlot(self, prepare):
		#PRINT("onOutgoingSlot", prepare)
		
		ready = self.prepareClipForSend(prepare)
		
		for question in ["Upload?", "Update?"]:
		
			if question == "Upload?":
				data = dict(container_name = ready["container_name"])
			if question == "Update?":
				data = ready
						
			send = dict(
				question = question,
				data = data
			)

			self.OUTGOING_QUEUE.append(send)
	
	def run(self): #It arranges for the object’s run() method to be invoked in a separate thread of control.
		#GEVENT OBJECTS CANNOT BE RUNNED OUTSIDE OF THIS THREAD, OR ELSE CONTEXT SWITCHING (COROUTINE YIELDING) WILL FAIL! THIS IS BECAUSE QTHREAD IS NOT MONKEY_PATCHABLE
	
		self.INCOMMING_UPDATE_EVENT = AsyncResult()
		self.INCOMMING_UPLOAD_EVENT = AsyncResult()
	
		self.wsock = WebSocketClient(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email="himeldas@live.com", password="faggotass", ) ) #The geventclient's websocket MUST be runned here, as running it in __init__ would put websocket in main thread
		self.wsock.connect()
	
		self.greenlets = [
			gevent.spawn(self.outgoingGreenlet),
			gevent.spawn(self.incommingGreenlet),
		]
		
		self.green = gevent.joinall(self.greenlets)

	def incommingGreenlet(self):
	
		while 1:

			PRINT("Begin Incomming Greenlet", "")
		
			dump = self.wsock.receive()
			#PRINT("received", dump)
			received = json.loads(str(dump)) #blocks
			
			answer = received["answer"]
			
			data   = received["data"]
			
			if answer == "Upload!":
				
				self.INCOMMING_UPLOAD_EVENT.set(data) #true or false
						
			if answer == "Update!": #there is an update
				
				self.INCOMMING_UPDATE_EVENT.set(data) #secure hash
				
				self.downloadClipFileIfNotExist(data)
				
				self.incommingSignalForMain.emit(data)
				
			gevent.sleep(1)

	def outgoingGreenlet(self):

		while 1:
		
			PRINT("Begin Outgoing Greenlet", "")
			
			gevent.sleep(1)
			
			try:
				send = self.OUTGOING_QUEUE.pop()
			except IndexError:
				continue
			else:
				data = send["data"]
				question = send["question"]
				
			if question == "Upload?":
				
				while 1: #mimic do while to prevent waiting before send
				
					self.wsock.send(json.dumps(send))
					
					upload_event = self.INCOMMING_UPLOAD_EVENT.wait(timeout=5) #AsyncResult.get will block until a result is set by another greenlet, after that get will not block anymore. NOTE- get will return exception! Use wait instead 

					if upload_event != None:
						break
						
				self.INCOMMING_UPLOAD_EVENT = AsyncResult()
					
				if upload_event == True:
									
					try:
						r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), files={"upload": open(container_path, 'rb')})
						print r
					except requests.exceptions.ConnectionError:
						pass #self.webSocketReconnect()
			
			if question == "Update?":
						
				while 1:
				
					self.wsock.send(json.dumps(send))
				
					if data.get("secure_hash") == (self.INCOMMING_UPDATE_EVENT.wait(timeout = 5) or {}).get("secure_hash"): #blocks at self.server_clip_hash.get() because it is an asyncresult (event) #keep sending until
						break
					
				self.INCOMMING_UPDATE_EVENT = AsyncResult() #reset the event
				
	def prepareClipForSend(self, prepare):
		
		clip_type = prepare["clip_type"]
		
		file_names = prepare["file_names"]
		
		secure_hash = prepare["secure_hash"]
		
		clip_display = prepare["clip_display"]
		
		with encompress.Encompress(password = "nigger", directory = self.temp_dir, file_names_encrypt = [file_names, secure_hash], file_name_decrypt=False) as container_name: #salt = clip_hash_secure needed so that files with the same name do not result in same hash, if the file data is different, since clip_hash_secure is generated from the file contents
			
			PRINT("encompress", container_name)

			#self.SEND_ID = uuid.uuid4() #change to sender id
				
			clip_content = {
				"clip_type" : clip_type,
				"clip_display" : clip_display,
				"container_name" : container_name,
				"secure_hash" : secure_hash, 
				"timestamp_client" : time.time(),
				#"send_id" : str(self.SEND_ID),
			}
			
			return clip_content
		
			
	def downloadClipFileIfNotExist(self, data):
		container_name = data["container_name"]
		container_path = os.path.join(self.temp_dir, container_name)
		print container_path
		
		if os.path.isfile(container_path):
			return container_path
		else:
			#TODO- show downloading file dialogue
			try:
				#urllib.urlretrieve(URL(arg="static/%s"%container_name,port=8084,scheme="http"), container_path)
				urllib.URLopener().retrieve(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "static", container_name), container_path) #http://stackoverflow.com/questions/1308542/how-to-catch-404-error-in-urllib-urlretrieve
			except IOError:
				pass
			else:
				return container_path
				
			