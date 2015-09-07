#--coding: utf-8 --

import gevent
from gevent.event import AsyncResult

#from gevent.queue import Queue #CANNOT USE QUEUE BECAUSE GEVENT CANNOT SWITCH CONTEXTS BETWEEN THREADS

from functions import *

import requests, datetime, socket

#from ws4py.client.geventclient import WebSocketClient
from websocket import create_connection
from websocket import _exceptions
from PySide.QtGui import *
from PySide import QtCore

import encompress

#DEFAULT_DOMAIN = "192.168.0.191"
DEFAULT_DOMAIN = "192.168.0.7"
DEFAULT_PORT = 8084

class WebsocketWorkerMixinForMain(object):

	FILE_ICONS = map(lambda file_icon: file_icon.split()[-1].upper(), os.listdir(os.path.normpath("images/files") ) )

	outgoingSignalForWorker = QtCore.Signal(dict)	
	
	def onIncommingSlot(self, emitted):
		#print emitted #display clips here
		
		new_clip = emitted
		
		#if not new_clip["sender_uuid"] == self.SENDER_UUID: #DO NOT set clipboard if new_clip with same sender ID as this will result in double, and possibly infinite list items. 
		#self.setClip()
		
		itm =  QListWidgetItem()
		
		if new_clip["clip_type"] == "screenshot":
			#crop and reduce pmap size to fit square icon
			image = QImage()
			#print "\n\n\n"
			print image.loadFromData(new_clip["clip_display"]["thumb"])
			itm.setIcon(QIcon(QPixmap(image)))
			txt = new_clip["clip_display"]["text"]
			
		elif new_clip["clip_type"] == "html":
			itm.setIcon(QIcon("images/text.png"))
			txt = new_clip["clip_display"]
			
		elif new_clip["clip_type"] == "text":
			itm.setIcon(QIcon("images/text.png"))
			txt = new_clip["clip_display"]
			
		elif new_clip["clip_type"] == "files":
			itm.setIcon(QIcon("images/files.png"))
			files = []
			for each_filename in new_clip["clip_display"]:
				ext = each_filename.split(".")[-1]
				file_icon = "files/%s"%ext
				if not ext.upper() in self.FILE_ICONS:
					pass#file_icon = os.path.normpath("files/_blank")
				if ext == "_folder": #get rid of the ._folder from folder._folder
					each_filename = each_filename.split(".")[0]
				files.append(u"{icon} {file_name}".format( #do NOT do "string {thing}".format(thing = u"unicode), or else unicode decode error will occur, the first string must be u"string {thing}"
					file_name = each_filename,
					icon = self.ICON_HTML.format(name=file_icon, side=32)
				))
			txt = "<br>".join(files)
				
		#PRINT("thumb on new_clip.data", new_clip["clip_display"])
		itm.setData(QtCore.Qt.UserRole, json.dumps(new_clip)) #json.dumps or else clip data (especially BSON's Binary)will be truncated by setData 
		
		if new_clip.get("starred")==True:
			list_widget = self.panel_stacked_widget.star_list_widget
		else:
			list_widget = self.panel_stacked_widget.main_list_widget
		
		list_widget.insertItem(0,itm) #add to top #http://www.qtcentre.org/threads/44672-How-to-add-a-item-to-the-top-in-QListWidget
		list_widget.takeItem(5)
		
		space = "&nbsp;"*8
		timestamp_human = u'{dt:%I}:{dt:%M}:{dt:%S}{dt:%p}{space}<span style="color:grey">{dt.month}-{dt.day}-{dt.year}</span>'.format(space = space, dt=datetime.datetime.fromtimestamp(new_clip["timestamp_server"] ) ) #http://stackoverflow.com/questions/904928/python-strftime-date-without-leading-0
		custom_label = QLabel(u"<b>{host_name}</b>{space}{timestamp}<pre>{text}</pre>".format(space = space, host_name = new_clip["host_name"], timestamp = timestamp_human, text=txt ) )
		custom_label.setOpenExternalLinks(True) ##http://stackoverflow.com/questions/8427446/making-qlabel-behave-like-a-hyperlink
		
		#resize the listwidget item to fit the html Qlabel, using Qlabel's sizehint
		list_widget.setItemWidget(itm, custom_label ) #add the label
		itm.setSizeHint( custom_label.sizeHint() ) #resize
		
		#move the scrollbar to top
		list_widget_scrollbar = list_widget.verticalScrollBar() #http://stackoverflow.com/questions/8698174/how-to-control-the-scroll-bar-with-qlistwidget
		list_widget_scrollbar.setValue(0)
					
class WebsocketWorker(QtCore.QThread):

	#This is the signal that will be emitted during the processing.
	#By including int as an argument, it lets the signal know to expect
	#an integer argument when emitting.
	incommingClipsSignalForMain = QtCore.Signal(dict)
	setClipSignalForMain = QtCore.Signal(dict)
	statusSignalForMain = QtCore.Signal(tuple)
	deleteClipSignalForMain = QtCore.Signal(list)
	StarClipSignalForMain = QtCore.Signal(dict)
	clearListSignalForMain = QtCore.Signal()
	session_id = uuid.uuid4()

	#You can do any extra things in this init you need, but for this example
	#nothing else needs to be done expect call the super's init
	def __init__(self, main):
		QtCore.QThread.__init__(self)
				
		self.main = main
		self.CONTAINER_DIR = self.main.CONTAINER_DIR
		self.main.outgoingSignalForWorker.connect(self.onOutgoingSlot) #we have to use slots as gevent cannot talk to separate threads that weren't monkey_patched (QThreads are not monkey_patched since they are not pure python)
		
		self.OUTGOING_QUEUE = deque() #must use alternative Queue for non standard library thread and greenlets
		
	#A QThread is run by calling it's start() function, which calls this run()
	#function in it's own "thread". 
	
	def onOutgoingSlot(self, async_process):
		#PRINT("onOutgoingSlot", prepare)
		
		data = async_process["data"]
		question = async_process["question"]
				
		if question == "Delete?":
			pass #nothing to process
			
		if question == "Star?":
			pass
		
		if question == "Update?": #do cpu intesive data modification before sending

			if not data.get("container_name"): ##CHECK HERE IF CONTAINER EXISTS IN OTHER ITEMS
				file_names = data["file_names"]
				self.statusSignalForMain.emit(("encrypting", "lock"))
				with encompress.Encompress(password = "nigger", directory = self.CONTAINER_DIR, file_names_encrypt = file_names) as container_name: 					
					
					data["container_name"] = container_name
					PRINT("encompress", container_name)
			
		
		data['host_name'] = self.main.HOST_NAME

		data["timestamp_client"] = time.time()	
		
		data["session_id"] = self.session_id
				
		send = dict(
			question = question,
			data=data
		)
		
		self.OUTGOING_QUEUE.append(send)
	
	def run(self): #It arranges for the object’s run() method to be invoked in a separate thread of control.
		#GEVENT OBJECTS CANNOT BE RUNNED OUTSIDE OF THIS THREAD, OR ELSE CONTEXT SWITCHING (COROUTINE YIELDING) WILL FAIL! THIS IS BECAUSE QTHREAD IS NOT MONKEY_PATCHABLE
	
		self.RESPONDED_EVENT = AsyncResult() #keep events separate, as other incomming events may interfere and crash the app! Though TCP/IP guarantees in-order sending and receiving, non-determanistic events like "new clips" will definitely fuck up the order!
		#self.RESPONDED_LIVING_EVENT = AsyncResult()
		
		self.RECONNECT = lambda: create_connection(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email=self.main.getLogin().get("email"), password=self.main.getLogin().get("password"), ) ) #The geventclient's websocket MUST be runned here, as running it in __init__ would put websocket in main thread
		
		self.WSOCK = None
		
		self.KEEP_RUNNING = 1
		
		self.greenlets = [
			gevent.spawn(self.outgoingGreenlet),
			gevent.spawn(self.incommingGreenlet),
			#gevent.spawn(self.keepAliveGreenlet),
		]
		
		self.green = gevent.joinall(self.greenlets)
		
	def workerLoopDecorator(workerGreenlet):
		def closure(self):
			while 1:
				if not self.KEEP_RUNNING: 
					continue #needed when username/password is incorrect, to pause the loop until a new password is set
				gevent.sleep(1)
				if self.WSOCK:
					try:
						workerGreenlet(self)
					except (socket.error, _exceptions.WebSocketConnectionClosedException):
						PRINT("failure in", workerGreenlet.__name__)
						self.statusSignalForMain.emit(("Reconnecting", "connect"))
						self.WSOCK.close() #close the WSOCK
					else:
						continue
				try: #TODO INVOKE CLIP READING ON STARTUP! AFTER CONNECTION
					self.WSOCK = self.RECONNECT()
					self.clearListSignalForMain.emit() #clear list on reconnect or else a new list will be sent on top of previous
				except: #previous try will handle later
					pass #block thread until there is a connection
		return closure
				
	@workerLoopDecorator
	def incommingGreenlet(self):
	
		PRINT("Begin Incomming Greenlet", "")
	
		dump = self.WSOCK.recv()

		try:
			received = json.loads(str(dump)) #blocks
		except ValueError: #occurs when socket closes unexpectedly
			raise socket.error
	
		answer = received["answer"]
		
		data   = received["data"]
		
		#Keep alive is handled by the websocket library itself (ie. it sends "alive?" pings that was done manually befor)

		#NON RESPONDED (non-determanistic)
		if answer == "Error!":
			self.KEEP_RUNNING = 0
			self.statusSignalForMain.emit((data, "bad"))
			
		elif answer == "Connected!":
			if not hasattr(self,"initialized"):
				self.statusSignalForMain.emit(("connected", "good"))
				self.initialized = 1
			else:
				self.statusSignalForMain.emit(("reconnected", "good"))
			
		elif answer == "Newest!":
			data.reverse() #so the clips can be displayed top down since each clip added gets pushed down in listwidget
			self.statusSignalForMain.emit(("downloading", "download"))
			for each in data:
			
				self.downloadContainerIfNotExist(each) #TODO MOVE THIS TO AFTER ONDOUBLE CLICK TO SAVE BANDWIDTH #MUST download container first, as it may not exist locally if new clip is from another device
				self.incommingClipsSignalForMain.emit(each)
				
			lastest = each
			
			not_this_device = lastest["session_id"] != self.session_id
			is_star = lastest.get("starred")

			if not_this_device and not is_star: #do not allow setting from the same pc
				self.setClipSignalForMain.emit(lastest) #this will set the newest clip only, thanks to self.main.new_clip!!!
				#container_names will NOT be reused as setClipSignalForMain will cause a new outgoing signal when the hashes change. This will result in unecessary uploads. The only way to resolve this is to make a hashtable
				
			if is_star:
				self.statusSignalForMain.emit(("starred", "good"))	
			else:
				self.statusSignalForMain.emit(("clip copied","good"))

		#RESPONDED (Handle data in outgoing_greenlet since it was the one that is expecting a response in order to yield control)
		elif answer in ["Upload!", "Update!", "Delete!", "Star!"]:
			self.RESPONDED_EVENT.set(received) #true or false	
		
	def sendUntilAnswered(self, send):
		while 1: #mimic do while to prevent waiting before send #TODO PREVENT DUPLICATE SENDS USING UUID
		
			expect = uuid.uuid4()
				
			send["echo"] = expect #prevents responses coming after 5 seconds from being accepted
		
			self.WSOCK.send(json.dumps(send))
						
			received = self.RESPONDED_EVENT.wait(timeout=5) #AsyncResult.get will block until a result is set by another greenlet, after that get will not block anymore. NOTE- get will return exception! Use wait instead 
			
			inspect = received["echo"]
			
			if received != None and expect == inspect:
				self.RESPONDED_EVENT = AsyncResult() #setattr(self, event_name, AsyncResult()	)
				break
						
		return received["data"]

	@workerLoopDecorator
	def outgoingGreenlet(self):
		
		#PRINT("Begin Outgoing Greenlet", "")
					
		#self.keepAlive()
					
		try:
			send = self.OUTGOING_QUEUE.pop()
		except IndexError:
			return
		else:
			data_out = send.get("data")
			question = send["question"]
			
		if question == "Update?":
					
			container_name = data_out["container_name"]
			container_path = os.path.join(self.CONTAINER_DIR, container_name)
							
			self.statusSignalForMain.emit(("uploading", "upload"))
			#first check if upload needed before updating
			container_exists = self.sendUntilAnswered(dict(
				question = "Upload?",
				data = container_name
			))
			
			if container_exists == False:

				try:
					r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), files={"upload": open(container_path, 'rb')})
				except requests.exceptions.ConnectionError:
					#connection error
					raise socket.error 
			
			self.statusSignalForMain.emit(("updating", "sync"))

			data_in = self.sendUntilAnswered(send)
								
			self.statusSignalForMain.emit(("updated", "good"))

				
		elif question=="Delete?":
			
			self.statusSignalForMain.emit(("deleting", "trash"))
			
			data_in = self.sendUntilAnswered(send)
			
			if data_in["success"] == True:
				self.deleteClipSignalForMain.emit(data_in["location"])
				self.statusSignalForMain.emit(("deleted", "good"))
			else:
				self.statusSignalForMain.emit(("already deleted", "warn"))
					
		elif question=="Star?":
		
			self.statusSignalForMain.emit(("starring", "star"))
			data_in = self.sendUntilAnswered(send)
			
			if data_in["success"] == False:
				self.statusSignalForMain.emit((data_in["reason"], "warn"))
			
			#self.starClipSignalForMain.emit(data_in)
				
			
	def downloadContainerIfNotExist(self, data):
		container_name = data["container_name"]
		container_path = os.path.join(self.CONTAINER_DIR, container_name)
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

