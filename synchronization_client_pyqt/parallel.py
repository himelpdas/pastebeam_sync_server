# coding=utf8

import gevent
from gevent.event import AsyncResult

#from gevent.queue import Queue #CANNOT USE QUEUE BECAUSE GEVENT CANNOT SWITCH CONTEXTS BETWEEN THREADS

from functions import *

import requests, datetime, socket

#from ws4py.client.geventclient import WebSocketClient
from websocket import create_connection
from PySide.QtGui import *
from PySide import QtCore

import encompress

DEFAULT_DOMAIN = "192.168.0.191"
DEFAULT_PORT = 8084

class WebsocketWorkerMixin(object):

	outgoingSignalForWorker = QtCore.Signal(dict)	
	
	def onIncommingSlot(self, emitted):
		#print emitted #display clips here
		itm =  QListWidgetItem()
		
		if emitted["clip_type"] == "screenshot":
			#crop and reduce pmap size to fit square icon
			image = QImage()
			#print "\n\n\n"
			print image.loadFromData(emitted["clip_display"]["thumb"])
			itm.setIcon(QIcon(QPixmap(image)))
			txt = emitted["clip_display"]["text"]
			
		elif emitted["clip_type"] == "html":
			itm.setIcon(QIcon("images/text.png"))
			txt = emitted["clip_display"]		
			
		elif emitted["clip_type"] == "text":
			itm.setIcon(QIcon("images/text.png"))
			txt = emitted["clip_display"]
			
		elif emitted["clip_type"] == "files":
			itm.setIcon(QIcon("images/files.png"))
			display_html = "<ul>{li}</ul>"
			unordered = []
			for each_filename in emitted["clip_display"]:
				unordered.append("<li>{file_name}</li>".format(file_name = each_filename) )
			txt = display_html.format(li="".join(unordered))
				
			
		itm.setData(QtCore.Qt.UserRole, dict(
			id = emitted["_id"],
			container_name = emitted["container_name"],
			clip_type = emitted["clip_type"]
		)) 
			
		#self.list_widget.addItem(itm) #or self.list_widget.addItem("some text") (different signature)
		self.list_widget.insertItem(0,itm) #add to top #http://www.qtcentre.org/threads/44672-How-to-add-a-item-to-the-top-in-QListWidget
		
		space = "&nbsp;"*7
		timestamp_human = '{dt:%I}:{dt:%M}:{dt:%S}{dt:%p}{space}<span style="color:grey">{dt.month}-{dt.day}-{dt.year}</span>'.format(space = space, dt=datetime.datetime.fromtimestamp(emitted["timestamp_server"] ) ) #http://stackoverflow.com/questions/904928/python-strftime-date-without-leading-0
		custom_label = QLabel("<html><b>{host_name}</b>{space}{timestamp}<pre>{text}</pre></html>".format(space = space, host_name = emitted["host_name"], timestamp = timestamp_human, text=txt ) )
		custom_label.setOpenExternalLinks(True) ##http://stackoverflow.com/questions/8427446/making-qlabel-behave-like-a-hyperlink
		
		self.list_widget.setItemWidget(itm, custom_label ) #add the label
		itm.setSizeHint( custom_label.sizeHint() ) #resize
					
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
		self.TEMP_DIR = self.main.TEMP_DIR
		self.main.outgoingSignalForWorker.connect(self.onOutgoingSlot) #we have to use slots as gevent cannot talk to separate threads that weren't monkey_patched (QThreads are not monkey_patched since they are not pure python)
		
		self.OUTGOING_QUEUE = deque() #must use alternative Queue for non standard library thread and greenlets
		
	#A QThread is run by calling it's start() function, which calls this run()
	#function in it's own "thread". 
	
	def onOutgoingSlot(self, data):
		#PRINT("onOutgoingSlot", prepare)

		file_names = data["file_names"]
		
		if not data.get("container_name"): ##CHECK HERE IF CONTAINER EXISTS IN OTHER ITEMS
		
			with encompress.Encompress(password = "nigger", directory = self.TEMP_DIR, file_names_encrypt = file_names) as container_name: 					
				
				data["container_name"] = container_name
				
		PRINT("encompress", container_name)
			
		data["timestamp_client"] = time.time()	
		
		send = dict(
			question = "Update?",
			data=data
		)

		self.OUTGOING_QUEUE.append(send)
	
	def run(self): #It arranges for the object’s run() method to be invoked in a separate thread of control.
		#GEVENT OBJECTS CANNOT BE RUNNED OUTSIDE OF THIS THREAD, OR ELSE CONTEXT SWITCHING (COROUTINE YIELDING) WILL FAIL! THIS IS BECAUSE QTHREAD IS NOT MONKEY_PATCHABLE
	
		self.INCOMMING_UPDATE_EVENT = AsyncResult()
		self.INCOMMING_NEWEST_EVENT = AsyncResult()
		self.INCOMMING_UPLOAD_EVENT = AsyncResult()
		
		self.greenlets = [
			gevent.spawn(self.outgoingGreenlet),
			gevent.spawn(self.incommingGreenlet),
		]
		
		self.green = gevent.joinall(self.greenlets)
		
	def workerLoopDecorator(workerGreenlet):
		def closure(self):
			while 1:
				try:
					workerGreenlet(self)
				except (AttributeError, socket.error):
					self.wsock = create_connection(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email="himeldas@live.com", password="faggotass", ) ) #The geventclient's websocket MUST be runned here, as running it in __init__ would put websocket in main thread
				gevent.sleep(1)
		return closure
	
	@workerLoopDecorator	
	def keepAliveGreenlet(self):
		pass
	
	@workerLoopDecorator
	def incommingGreenlet(self):
	
		PRINT("Begin Incomming Greenlet", "")
	
		dump = self.wsock.recv()
		#PRINT("received", dump)
		received = json.loads(str(dump)) #blocks
		
		answer = received["answer"]
		
		data   = received["data"]
		
		if answer == "Upload!":
		
			self.INCOMMING_UPLOAD_EVENT.set(data) #true or false
			
		if answer == "Newest!":
		
			self.INCOMMING_NEWEST_EVENT.set(data) #clip
			
			for each in data:
			
				self.incommingSignalForMain.emit(each)
				self.downloadContainerIfNotExist(each)
										
		if answer == "Update!":
			
			self.INCOMMING_UPDATE_EVENT.set(data) #clip	

	@workerLoopDecorator
	def outgoingGreenlet(self):
		
		PRINT("Begin Outgoing Greenlet", "")
					
		try:
			send = self.OUTGOING_QUEUE.pop()
		except IndexError:
			return
		else:
			data = send.get("data")
			question = send["question"]
			
		if question == "Update?":
		
			container_name = data["container_name"]
			container_path = os.path.join(self.TEMP_DIR, container_name)
							
			while 1:
				
				self.wsock.send(json.dumps(dict(
					question = "Upload?",
					data = container_name
				)))

				container_exists = self.INCOMMING_UPLOAD_EVENT.wait(timeout=5)
				
				if container_exists != None:
					self.INCOMMING_UPLOAD_EVENT = AsyncResult()	
					break
			
			if container_exists == False:

				try:
					r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), files={"upload": open(container_path, 'rb')})
				except requests.exceptions.ConnectionError:
					#connection error
					#self.webSocketReconnect()
					raise socket.error 
			
			while 1: #mimic do while to prevent waiting before send #TODO PREVENT DUPLICATE SENDS USING UUID
			
				self.wsock.send(json.dumps(send))
									
				data = self.INCOMMING_UPDATE_EVENT.wait(timeout=5) #AsyncResult.get will block until a result is set by another greenlet, after that get will not block anymore. NOTE- get will return exception! Use wait instead 
				
				if data != None:
					self.INCOMMING_UDATE_EVENT = AsyncResult()	
					break
					
				PRINT("update",data)
				
			
	def downloadContainerIfNotExist(self, data):
		container_name = data["container_name"]
		container_path = os.path.join(self.TEMP_DIR, container_name)
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
				
			