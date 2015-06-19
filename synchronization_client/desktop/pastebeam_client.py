# -*- coding: utf8 -*-
from gevent import monkey; monkey.patch_all() #no need to monkeypatch all, just sockets... Now we can bidirectionally communicate, unlike with blocking websocket client
from gevent.event import AsyncResult
import gevent

import keyring

#socket stuff
from ws4py.client.geventclient import WebSocketClient
from ws4py import exc
from socket import error as SocketError
##from websocket import create_connection #old blocking library useless for bidirectional, might as well stick to long-polling then
#http stuff
import requests
from requests import ConnectionError

#ui stuff
import wx
from threading import Thread # import * BREAKS enumerate!!!
from wxpython_view import *

#general stuff
import time, sys, zlib, datetime, uuid, os, tempfile, urllib, gc, hashlib, shutil,json 
import distutils.file_util, distutils.dir_util, distutils.errors #must import like this else import error in pyinstaller
from functions import *
import encompress

#debug
import pdb

#db stuff
#import mmh3
from spooky import hash128
import bson.json_util as json

DEFAULT_DOMAIN = "192.168.0.191"
DEFAULT_PORT = 8084

def URL(scheme, addr, port, *_args, **_vars): 
	url = "{scheme}://{addr}:{port}/".format(scheme=scheme, addr=addr, port=port)
	if _args:
		args = "/".join(_args)
		url+=args
	if _vars:
		url+="?"
		for key, value in _vars.items():
			url+="{key}={value}&".format(key=key, value=value)
		url=url[:-1]
	return url

TEMP_DIR = tempfile.mkdtemp(); print TEMP_DIR

MAX_FILE_SIZE = 1024*1024*50

FILE_IGNORE_LIST = map(lambda each: each.upper(), ["desktop.ini","thumbs.db",".ds_store","icon\r",".dropbox",".dropbox.attr"]) #https://www.dropbox.com/en/help/145 and http://stackoverflow.com/questions/15835213/list-of-various-system-files-safe-to-ignore-when-implementing-a-virtual-file-sys

# Button definitions
ID_START = wx.NewId()
ID_STOP = wx.NewId()

# Define notification event for thread completion
EVT_RESULT_ID = wx.NewId()

def BIND_EVT_RESULT(win, func):
	"""Define Result Event."""
	win.Connect(-1, -1, EVT_RESULT_ID, func)

class EVT_RESULT(wx.PyEvent):
	"""Simple event to carry arbitrary result data."""
	def __init__(self, data):
		"""Init Result Event."""
		wx.PyEvent.__init__(self)
		self.SetEventType(EVT_RESULT_ID)
		self.data = data

#interthread communication
#lock = Lock() #locks not needed in gevent, use AsyncResult
#with lock:
#...
SEND_ID = None
SERVER_LATEST_CLIP, CLIENT_LATEST_CLIP, CLIENT_RECENT_DATA = AsyncResult(), AsyncResult(), AsyncResult()
SERVER_LATEST_CLIP.set({}) #the latest clip's hash on server
CLIENT_LATEST_CLIP.set({}) #the latest clip's hash on client. Take no action if equal with above.
CLIENT_RECENT_DATA.set(None)
#HOST_CLIP_CONTENT.set(None) #the raw clip content from the client

class WorkerThread(Thread):
	"""Worker Thread Class."""

	KEEP_RUNNING = True
	ACCOUNT_SALT = False
	FORCE_RECONNECT = False
	
	def __init__(self, notify_window):
		"""Init Worker Thread Class."""
		Thread.__init__(self)
		self._notify_window = notify_window
		#self.KEEP_RUNNING = True
		# This starts the thread running on creation, but you could
		# also make the GUI thread responsible for calling this
		self.start()

	#@classmethod #similar to static, but passes the class as the first argument... useful for modifying static variables
	def pause(self):
		"""abort worker thread."""
		# Method for use by main thread to signal an abort
		self.KEEP_RUNNING = False
		self._notify_window.sb.toggleSwitchIcon(on=False)
		self._notify_window.sb.clear()
		self._notify_window.toggle_item.SetText("Resume PasteBeam")
		
	def resume(self):
		self.KEEP_RUNNING = True
		self._notify_window.sb.toggleSwitchIcon(on=True)
		self._notify_window.sb.clear()
		self._notify_window.toggle_item.SetText("Pause PasteBeam")
		
	def restart(self):
		self.resume()
		self.FORCE_RECONNECT = True #this is needed to refresh the password on server
		self.ACCOUNT_SALT = False
		
class WebSocketThread(WorkerThread):
	"""
	Websocket.receive() blocks until there is a response.
	It also hangs indefinitely until there is socket.close() call in the server side
	If the server shuts down unexpectedly the client socket.recieve() will hang forever.
	
	"""
	
	def __init__(self, notify_window):
		#self.webSocketReconnect() #because threads have been "geventified" they no longer run in parallel, but rather asynchronously. So if this runs not within a greenlet, it will block the mainloop... gevent.sleep(1) only yields to another greenlet or couroutine (like wx.Yield) when it is called from within a greenlet.
		
		self.last_sent = self.last_alive = datetime.datetime.now()
		
		self.containers_in_server = {}
				
		WorkerThread.__init__(self, notify_window)
	
	def webSocketReconnect(self):
		"""
		WSock.receive sometimes hangs, as in the case of a disconnect
		Receive blocks, but send does not, so we use send as a tester
		An ideal connection will have a 1:1 ratio of send and receive
		However, bad connections will have poorer ratios such as 10:1
		If ratio reaches 20:1 then this function will force reconnect
		This function is triggered when CLIENT_LATEST_CLIP is set, but
		SERVER_LATEST_CLIP is not, and the outgoing loop keeps calling
		"""
		while 1:
			if self.KEEP_RUNNING:
				try:
					self.wsock.close_connection() # Terminate Nones the environ and stream attributes, which is for servers
				except AttributeError:
					pass
				try:
					self.last_sent = self.last_alive = datetime.datetime.now()
					
					login = self._notify_window.getLogin()
					self.wsock=WebSocketClient(URL("ws",DEFAULT_DOMAIN, DEFAULT_PORT, "ws", email=login.get("email") or "", password=login.get("password" or ""), ) ) #email="test@123.com", password="test4567" #keep static to guarantee one socket for all instances
					
					self.wsock.connect()
					break
				except (SocketError, exc.HandshakeError, RuntimeError):
					print "no connection..."
					self._notify_window.destroyBusyDialog()
					self._notify_window.sb.toggleStatusIcon(msg="Unable to connect to the internet.", icon="bad")
			gevent.sleep(1)
				
	def keepAlive(self, heartbeat = 100, timeout = 1000): #increment of 60s times 20 unresponsive = 20 minutes
		"""
		Since send is the only way we can test a connection's status,
		and since send is only triggered when CLIENT_LATEST_CLIP has a
		change, we need to test the connection incrementally too, and
		therefore we can account for when the user is idle.
		"""
		now = datetime.datetime.now()
		if self.FORCE_RECONNECT or ( now - self.last_alive ).seconds > timeout:
			self.webSocketReconnect()
			self.FORCE_RECONNECT = False
		elif ( now  - self.last_sent ).seconds > heartbeat:
			self.last_sent= datetime.datetime.now()
			return True
		return False
	
	def incoming(self):
		#pdb.set_trace()
		#print "start incoming..."
		while 1:
			if self.KEEP_RUNNING:
				#if CLIENT_LATEST_CLIP.get() != SERVER_LATEST_CLIP.get():
				#print "getting... c:%s, s:%s"%(CLIENT_LATEST_CLIP.get(),SERVER_LATEST_CLIP.get())
				try:
					received = self.wsock.receive() #WebSocket run method is implicitly called, "Performs the operation of reading from the underlying connection in order to feed the stream of bytes." According to WS4PY This method is blocking and should likely be run in a thread.
					
					if received == None:
						raise SocketError #disconnected!
					
					delivered = json.loads(str(received) ) #EXTREME: this can last forever, and when creating new connection, this greenlet will hang forever. #receive returns txtmessage object, must convert to string!!! 
					
					if delivered["message"] == "Error!":
						print delivered["data"]
						self.pause()
						self._notify_window.sb.toggleStatusIcon(msg=delivered["data"], icon="bad")
					
					if delivered["message"] == "Salt!":
						print "\nSalt! %s\n"%delivered["data"]
						self.ACCOUNT_SALT = delivered["data"]
					
					if delivered["message"] == "Update!":
						server_latest_clip_rowS = delivered['data']
						server_latest_clip_row = server_latest_clip_rowS[0]
						#print server_latest_clip_row
						
						SERVER_LATEST_CLIP.set(server_latest_clip_row) #should move this to after postevent or race condition may occur, but since this is gevent, it might not be necessary
						CLIENT_LATEST_CLIP.set(server_latest_clip_row)
						
						#print "GET %s"% server_latest_clip_row['clip_hash_fast']
						
						wx.PostEvent(self._notify_window, EVT_RESULT(server_latest_clip_rowS) )
						
					elif delivered["message"] == "Upload!":
						self.containers_in_server.update(delivered['data'])
						
					elif delivered["message"] == "Alive!":
						print "Alive!"
						self.last_alive = datetime.datetime.now()
		
				#except (SocketError, RuntimeError, AttributeError, ValueError, TypeError): #gevent traceback didn't mention it was a socket error, just "error", but googling the traceback proved it was. #if received is not None: #test if socket can send
				except:
					#print "can't get...%s"%str(sys.exc_info()[0])
					self.webSocketReconnect()
				
			gevent.sleep(0.25)
				
	def outgoing(self):
		#pdb.set_trace()
		#print "start outgoing..."
		while 1:
			if self.KEEP_RUNNING:
				
				sendit = False
				
				if self.keepAlive(): #also send alive messages and reset connection if receive block indefinitely
					sendit = dict(message="Alive?")
					
				if not self.ACCOUNT_SALT:
					print "Salt?"
					sendit = dict(
						message="Salt?",
					)
				
				elif CLIENT_LATEST_CLIP.get().get('clip_hash_secure') != SERVER_LATEST_CLIP.get().get('clip_hash_secure'): #start only when there is something to send
					
					send_clip = CLIENT_LATEST_CLIP.get()
					
					#print "sending...%s"%send_clip	
					
					container_name = send_clip['container_name']
					container_path = os.path.join(TEMP_DIR,container_name)
					
					#response = requests.get(URL(arg="file_exists/%s"%container_name,port=8084,scheme="http"))
					#file_exists = json.loads(response.content)
					if not container_name in self.containers_in_server:
						print "UPLOAD? %s"%container_name
						sendit = dict(
									message="Upload?",
									data = container_name,
								)
					else:
						try:
							if self.containers_in_server[container_name] == False:
								r = requests.post(URL("http", DEFAULT_DOMAIN, DEFAULT_PORT, "upload"), files={"upload": open(container_path, 'rb')})
								print r
						except requests.exceptions.ConnectionError:
							#self.destroyBusyDialog()
							#self.sb.toggleStatusIcon(msg="Unable to connect to the internet.", icon=False)
							self.webSocketReconnect()
						else:
							sendit = dict(
								message="Update?",
								data=CLIENT_LATEST_CLIP.get(),
							)
							
							print "\nSEND %s... %s\n"%(CLIENT_LATEST_CLIP.get().get('clip_hash_secure'), SERVER_LATEST_CLIP.get().get('clip_hash_secure'))
							
							
				if sendit:
					try:
						self.wsock.send(json.dumps(sendit))
						
						self.last_sent = datetime.datetime.now()

					#except (SocketError, RuntimeError, AttributeError, ValueError, TypeError): #if self.wsock.stream: #test if socket can get
					except:
						#print "can't send...%s"%str(sys.exc_info()[0])
						self.webSocketReconnect()
						
			
			gevent.sleep(0.25) #yield to next coroutine.
		
	
	def run(self):
		greenlets = [
			gevent.spawn(self.outgoing),
			gevent.spawn(self.incoming),
		]
		gevent.joinall(greenlets)
		#or you can do this in separate threads but that is annoying,
		#since gevent monkey patches threads to gevent-like
				
class Main(wx.Frame, MenuBarMixin):
	#ID_NEW = 1
	#ID_RENAME = 2
	#ID_CLEAR = 3
	#ID_DELETE = 4
	TEMP_DIR = TEMP_DIR

	TEMP_EMAIL = ""
	TEMP_PASS = ""
	
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "PasteBeam")
		self._do_interface()
		self._do_threads_and_async()

	def _do_interface(self): #_ used because it is meant to be internal to instance
		self.panel = MyPanel(self)

		self.sb = MyStatusBar(self)
		self.SetStatusBar(self.sb)
		
		self.doMenuBar()

	def _do_threads_and_async(self):
		# Set up event handler for any worker thread results
		BIND_EVT_RESULT(self,self.onResult)
		# And indicate we don't have a worker thread yet
		self.websocket_worker = None
		# Temporary... no button event, so pass None
		
		self.setThrottle()
		wx.CallLater(1, lambda: self.onStart(None))
		
	@staticmethod
	def getLogin():
		ring = keyring.get_password("pastebeam","login")
		login = json.loads(ring) if ring else {} #todo store email locally, and access only password!
		return login

	def appendClipToListCtrl(self, clip, is_newest):
		clip_display_decoded = json.loads(clip['clip_display_decoded'])
		
		def _generate_display_human():
			if clip['clip_type'] in ["text", "link"]:	
				display_human =  clip_display_decoded[0]
			elif clip['clip_type'] == "bitmap":
				display_human = "Clipboard image (%s megapixels)" % clip_display_decoded[0]
			elif clip['clip_type'] == "files":
				file_names = clip_display_decoded
				
				number_of_files = len(file_names)
				file_or_files = "files" if number_of_files > 1 else "file"
				
				file_exts = sorted(set(map(lambda each_file_name: os.path.splitext(each_file_name)[1].strip(".").replace("_folder", "folder").upper() or "??", file_names))) #use set to prevent jpg, jpg, jpg
				file_exts_first = file_exts[:-1]
				file_exts_last = file_exts[-1]
				exts_sentence = ", ".join(file_exts_first)
				if file_exts_first:
					exts_sentence = exts_sentence + ("," if number_of_files > 2 else "") + " and " + file_exts_last
				else:
					exts_sentence = file_exts_last

				#display_human = "%s %s files"%(len(file_names), ", ".join(set(map(lambda each_file_name: os.path.splitext(each_file_name)[1].strip("."), file_names) ) ) )
				exts_human = "%s %s (%s): "%(number_of_files, file_or_files,exts_sentence)
				
				file_names = map(lambda each_name: each_name.replace("._folder",""), file_names)
				file_names_first = file_names[:-1]
				file_names_last = file_names[-1]
				names_sentence = ", ".join(file_names_first)
				if file_names_first:
					names_sentence = names_sentence + ("," if number_of_files > 2 else "") + " and " + file_names_last
				else:
					names_sentence = file_names_last

				display_human = "%s %s"%(exts_human, names_sentence)
			
			return display_human
	
		def _stylize_new_row():
			new_item_index = self.panel.lst.GetItemCount() - 1
			if (new_item_index % 2) != 0:
				#color_hex = '#E6FCFF' #second lightest at http://www.hitmill.com/html/pastels.html
				#color_hex = '#f1f1f1'
			#else:
				#color_hex = '#FFFFE3'
				
				self.panel.lst.SetItemBackgroundColour(new_item_index, "#f1f1f1") #many ways to set colors, see http://www.wxpython.org/docs/api/wx.Colour-class.html and http://wxpython.org/Phoenix/docs/html/ColourDatabase.html #win.SetBackgroundColour(wxColour(0,0,255)), win.SetBackgroundColour('BLUE'), win.SetBackgroundColour('#0000FF'), win.SetBackgroundColour((0,0,255))
						
			if clip['clip_type'] == "text":	
				file_image_number = self.panel.lst.icon_extensions.index("._clip")
				
			elif clip['clip_type'] == "files":
				file_names = clip_display_decoded
				if len(file_names) == 1:
					clip_file_ext = os.path.splitext(file_names[0])[1]
					try:
						file_image_number = self.panel.lst.icon_extensions.index(clip_file_ext) #http://stackoverflow.com/questions/176918/finding-the-index-of-an-item-given-a-list-containing-it-in-python
					except ValueError:
						file_image_number = self.panel.lst.icon_extensions.index("._blank")
				else:
					file_image_number = self.panel.lst.icon_extensions.index("._multi")
					
			elif clip['clip_type'] == "bitmap":
				file_image_number = self.panel.lst.icon_extensions.index("._bitmap")		
				
			elif clip['clip_type'] == "link":
				file_image_number = self.panel.lst.icon_extensions.index("._link")
				
			self.panel.lst.SetItemImage(new_item_index, file_image_number)
			#self.panel.lst.SetItemBackgroundColour(new_item_index, color_hex)
			
			if is_newest: #make bold if newest
				item = self.panel.lst.GetItem(new_index)
				#item.SetBackgroundColour("#B8B8B8")
				#item.SetTextColour("WHITE")
				font = item.GetFont()
				font.SetWeight(wx.FONTWEIGHT_BOLD)
				item.SetFont(font)
				self.panel.lst.SetItem(item)
			
		def _descending_order():
			self.panel.lst.SetItemData( new_index, new_index) #SetItemData(self, item, data) Associates data with this item. The data part is used by SortItems to compare two values via the ListCompareFunction
			self.panel.lst.SortItems(self.panel.lst.ListCompareFunction)
		
			
		#new_item_number_to_be = self.panel.lst.GetItemCount() + 1;  self.panel.lst.Append( (new_item_number_to_be...))
		#timestamp_human = datetime.datetime.fromtimestamp(clip['timestamp_server']).strftime(u'%H:%M:%S \u2219 %Y-%m-%d'.encode("utf-8") ).decode("utf-8") #broken pipe \u00A6
		id_human = clip["container_name"].split(".")[0]
		display_human =  _generate_display_human()
		timestamp_human = u'{dt:%I}:{dt:%M}:{dt:%S} {dt:%p} \u2219 {dt.month}-{dt.day}-{dt.year}'.format(dt=datetime.datetime.fromtimestamp(clip['timestamp_server'] ) ) #http://stackoverflow.com/questions/904928/python-strftime-date-without-leading-0
		new_index = self.panel.lst.Append( (clip['clip_type'], id_human, display_human,  clip['host_name'], timestamp_human ) ) #unicodedecode error fix	#http://stackoverflow.com/questions/2571515/using-a-unicode-format-for-pythons-time-strftime
		
		_stylize_new_row()
		
		_descending_order()
		
	def clearList(self):
		self.panel.lst.DeleteAllItems()

	def onStart(self, button_event):
		"""Start Computation."""
		self.websocket_worker = WebSocketThread(self)
		self.runAsyncWorker()

	def onQuit(self, event):
		#self.websocket_worker.KEEP_RUNNING = False
		#self.Close() #DOES NOT WORK
		self.sb.toggleStatusIcon(msg='Shutting down...', icon="bad")
		pid = os.getpid() #http://quickies.seriot.ch/?id=189
		os.kill(pid, 1)

	def onResult(self, result_event):
		"""Show Result status."""
		#if result_event.data is None:
		#	# Thread aborted (using our convention of None return)
		#	self.appendClipToListCtrl('Computation aborted\n')
		if result_event.data:
			# Process results here
			clip_list = result_event.data
			
			latest_content = clip_list[0]
			
			if latest_content['send_id'] != SEND_ID: #no point of setting new clipboard to the same machine that just uploaded it. Without this OS cut and paste will break.

				self.setClipboardContent(container_name= latest_content['container_name'], clip_type =latest_content['clip_type'])
			
			print "\nclip file name %s\n"%latest_content['container_name']
			
			oldest_to_newest_clips = clip_list[::-1] #reversed copy
			newest_index = len(oldest_to_newest_clips) - 1
			self.clearList()
			for item_index, each_clip in enumerate(oldest_to_newest_clips):
				#print each_clip
				try:
					#print "DECODE CLIP %s"%each_clip['clip_display_encoded']
					each_clip['clip_display_decoded'] = self.decodeClip(each_clip['clip_display_encoded'])
				except ZeroDivisionError:#(zlib.error, UnicodeDecodeError):
					newest_index-=1 #the list will be smaller if some items are duds, so make the newest_index smaller too
					#print "DECODE/DECRYPT/UNZIP ERROR"
				else:
					self.appendClipToListCtrl(each_clip, is_newest = (True if item_index==newest_index else False) )
					
		self.destroyBusyDialog()

		
	@staticmethod
	def decodeClip(clip):
		return (clip or '').decode("base64").decode("zlib").decode("utf-8", "replace")
	
	@staticmethod
	def encodeClip(clip):
		return (clip or '').encode("utf-8", "replace").encode("zlib").encode("base64") #MUST ENCODE in base64 before transmitting obsfucated data #null clip causes serious looping problems, put some text! Prevent setText's TypeError: String or Unicode type required 
		
	def downloadClipFileIfNotExist(self, container_name):
		container_path = os.path.join(TEMP_DIR,container_name)
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
				
	def destroyBusyDialog(self):
		#this will be invoked if another client has a new clip
		#so always check if busy_dialog in attributes
		if 'busy_dialog' in self.__dict__ and self.busy_dialog:
			self.busy_dialog.Destroy()
			self.busy_dialog = None
		self.SetTransparent( 255 )
		
	def showBusyDialog(self):
		self.busy_dialog = wx.BusyInfo("Retrieving clip. Please wait a moment...", self)
		self.SetTransparent( 222 )
		
	def setClipboardContent(self, container_name, clip_type): 
		#NEEDS TO BE IN MAIN LOOP FOR WRITING TO WORK, OR ELSE WE WILL 
		#GET SOMETHING LIKE: "Failed to put data on the clipboard 
		#(error 2147221008: coInitialize has not been called.)"
		success = False
		try:
			with wx.TheClipboard.Get() as clipboard:
	
				self.sb.toggleStatusIcon(msg='Downloading and decrypting %s data...'%clip_type, icon="unlock")
	
				container_path = self.downloadClipFileIfNotExist(container_name)
				
				if container_path:
					
					print "DECRYPT"
					with encompress.Encompress(password = "nigger", directory = TEMP_DIR, file_name_decrypt=container_name) as file_paths_decrypt:
						#print file_paths_decrypt
						
						if clip_type in ["text","link"]:
						
							clip_file_path = file_paths_decrypt[0]
						
							with open(clip_file_path, 'r') as clip_file:
								clip_text = self.decodeClip(clip_file.read())
								clip_data = wx.TextDataObject()
								clip_data.SetText(clip_text)
								success = clipboard.SetData(clip_data)

						elif clip_type == "bitmap":
						
							clip_file_path = file_paths_decrypt[0]
						
							bitmap=wx.Bitmap(clip_file_path, wx.BITMAP_TYPE_BMP)
							clip_data = wx.BitmapDataObject(bitmap)
							success = clipboard.SetData(clip_data)		
							
						elif clip_type == "files":
							clip_file_paths = file_paths_decrypt
							clip_data = wx.FileDataObject()
							for each_file_path in clip_file_paths:
								clip_data.AddFile(each_file_path)
							success = clipboard.SetData(clip_data)
				else:
					self.destroyBusyDialog()
					wx.MessageBox("Unable to download this clip from the server", "Error")

		except:
			wx.MessageBox("Unknown Error. (548)", "Error")
			self.destroyBusyDialog()
					
		if success:	
			self.sb.toggleStatusIcon(msg='Successfully received %s data.' % clip_type, icon="good")
		
		return success
		#PUT MESSAGEBOX HERE? ALSO destroyBusyDialog
		
	def getClipboardContent(self):
		try:
			with wx.TheClipboard.Get() as clipboard:
			
				def __prepare_for_upload(file_names, clip_type, clip_display, clip_hash_secure, compare_next):
						
					print "\nBLOCK!!!\n"
						
					self.sb.toggleStatusIcon(msg='Encrypting and uploading %s data...'%clip_type, icon="lock")
						
					with encompress.Encompress(password = "nigger", directory = TEMP_DIR, file_names_encrypt = [file_names, clip_hash_secure], file_name_decrypt=False) as container_name: #salt = clip_hash_secure needed so that files with the same name do not result in same hash, if the file data is different, since clip_hash_secure is generated from the file contents
						
						print "\ngetClipboardContent: container_name: %s\n"%container_name #salting the file_name will cause decryption to fail if

						global SEND_ID #change to sender id
						SEND_ID = uuid.uuid4()
							
						clip_content = {
							"clip_type" : clip_type,
							"clip_display_encoded" : self.encodeClip(json.dumps(clip_display)),
							"container_name" : container_name,
							"clip_hash_secure" : clip_hash_secure, #http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x
							"host_name" : self.getLogin().get("device_name"),
							"timestamp_client" : time.time(),
							"send_id" : SEND_ID,
						}
						
						CLIENT_RECENT_DATA.set(compare_next)
						#print "SETTED %s"%compare_next
						
						self.sb.toggleStatusIcon(msg='Successfully uploaded %s data.'%clip_type, icon="good")
						
						return clip_content
			
				def _return_if_text_or_url():
					clip_data = wx.TextDataObject()
					success = clipboard.GetData(clip_data)
					
					if success:
						self.setThrottle("fast")
					
						clip_text_old = CLIENT_RECENT_DATA.get()
						
						clip_text_new = clip_data.GetText()
						
						if clip_text_new != clip_text_old: #UnicodeWarning: Unicode equal comparison failed to convert both arguments to Unicode - interpreting them as being unequal
							clip_text_is_url = string_is_url(clip_text_new)
							
							clip_text_encoded = self.encodeClip(clip_text_new)
							
							if clip_text_is_url:
								clip_display =  clip_text_new
							else:
								clip_display = clip_text_new[:2000]

							clip_hash_fast = format( hash128( clip_text_encoded ), "x") #hex( hash128( clip_text_encoded ) ) #use instead to get rid of 0x for better looking filenames
							clip_hash_secure = hashlib.new("ripemd160", clip_hash_fast + self.websocket_worker.ACCOUNT_SALT).hexdigest()
														
							txt_file_name = "%s.txt"%clip_hash_secure
							txt_file_path = os.path.join(TEMP_DIR,txt_file_name)
							
							with open(txt_file_path, 'w') as txt_file:
								txt_file.write(clip_text_encoded)
								
							return __prepare_for_upload(
								file_names = [txt_file_name],
								clip_type = "text" if not clip_text_is_url else "link", 
								clip_display = [clip_display], 
								clip_hash_secure = clip_hash_secure, 
								compare_next = clip_text_new
							)
						
				def _return_if_bitmap():
					clip_data = wx.BitmapDataObject() #http://stackoverflow.com/questions/2629907/reading-an-image-from-the-clipboard-with-wxpython
					success = clipboard.GetData(clip_data)

					if success:
						self.setThrottle("slow")
						
						image_old = CLIENT_RECENT_DATA.get()
						#print "image_old %s"%image_old
						
						try: 
							image_old_buffer_array = image_old.GetDataBuffer() #SOLVED GetDataBuffer crashing! You need to ensure that you do not use this buffer object after the image has been destroyed. http://wxpython.org/Phoenix/docs/html/MigrationGuide.html bitmap.ConvertToImage().GetDataBuffer() WILL FAIL because the image is destroyed after GetDataBuffer() is called so doing a buffer1 != buffer2 comparison will crash
						except AttributeError:
							image_old_buffer_array = None #if prevuous is not an image
						
						bitmap = clip_data.GetBitmap()
						image_new  = bitmap.ConvertToImage() #OLD #GET DATA IS HIDDEN METHOD, IT RETURNS BYTE ARRAY... DO NOT USE GETDATABUFFER AS IT CRASHES. BESIDES GETDATABUFFER IS ONLY GOOD TO CHANGE BYTES IN MEMORY http://wxpython.org/Phoenix/docs/html/MigrationGuide.html
						image_new_buffer_array = image_new.GetDataBuffer()
																		
						if image_new_buffer_array != image_old_buffer_array: #for performance reasons we are not using the bmp for hash, but rather the wx Image GetData array
														
							clip_hash_fast = format(hash128(image_new_buffer_array), "x") #hex(hash128(image_new)) #KEEP PRIVATE and use to get hash of large data quickly
							clip_hash_secure = hashlib.new("ripemd160", clip_hash_fast + self.websocket_worker.ACCOUNT_SALT).hexdigest() #to prevent rainbow table attacks of known files and their hashes, will also cause decryption to fail if file name is changed
							
							img_file_name = "%s.bmp"%clip_hash_secure
							img_file_path = os.path.join(TEMP_DIR,img_file_name)
							
							print "\nimg_file_path: \n%s\n"%img_file_path
							
							bitmap.SaveFile(img_file_path, wx.BITMAP_TYPE_BMP) #change to or compliment upload
							
							megapixels = len(image_new_buffer_array) / 3
							
							clip_display = megapixels
							
							"""
							print "ENCRYPT"
							with encompress.Encompress(password = "nigger", directory = TEMP_DIR, file_names_encrypt = [img_file_name], file_name_decrypt=False) as result:
								print result #salting the file_name will cause decryption to fail if
								
							print "DECRYPT"
							with open(result, "rb") as file_name_decrypt:
								with encompress.Encompress(password = "nigger", directory = TEMP_DIR, file_names_encrypt = [img_file_name], file_name_decrypt=file_name_decrypt) as result:
									print result
							"""
							
							try:
								image_old.Destroy()
							except AttributeError:
								pass	
							
							return __prepare_for_upload(
								file_names = [img_file_name],
								clip_type = "bitmap", 
								clip_display = [clip_display], 
								clip_hash_secure = clip_hash_secure, 
								compare_next = image_new
							)
						else:
							image_new.Destroy() #clear memory
							#gc.collect() #free up previous references to image_new and image_old arrays, since they are so large #http://stackoverflow.com/questions/1316767/how-can-i-explicitly-free-memory-in-python

				def _return_if_file():
					clip_data = wx.FileDataObject()
					success = clipboard.GetData(clip_data)

					if success:
						self.setThrottle("slow")
	
						os_file_paths_new = sorted(clip_data.GetFilenames())
						
						try:
							os_file_sizes_new = map(lambda each_os_path: getFolderSize(each_os_path, max=MAX_FILE_SIZE) if os.path.isdir(each_os_path) else os.path.getsize(each_os_path), os_file_paths_new)
						except:
							return
						
						if sum(os_file_sizes_new) > MAX_FILE_SIZE:
							self.sb.toggleStatusIcon(msg='Files not uploaded. Maximum files size is 50 megabytes.', icon="bad")
							return #upload error clip

						#print os_file_paths_new
										
						os_file_hashes_old_set = CLIENT_RECENT_DATA.get()
						os_file_hashes_new = []
						
						os_file_names_new = []
						display_file_names =[]
						

						try:

							for each_path in os_file_paths_new:
							
								each_file_name = os.path.split(each_path)[1]
							
								os_file_names_new.append(each_file_name)
								
								if os.path.isdir(each_path):
								
									display_file_names.append(each_file_name+" folder (%s inside)"%len(os.listdir(each_path))+"._folder")
								
									os_folder_hashes = []
									for dirName, subdirList, fileList in os.walk(each_path, topdown=False):
										subdirList = filter
										for fname in fileList:
											if fname.upper() not in FILE_IGNORE_LIST: #DO NOT calculate hash for system files as they are always changing, and if a folder is in clipboard, a new upload may be initiated each time a system file is changed
												each_sub_path = os.path.join(dirName, fname)
												with open(each_sub_path, 'rb') as each_sub_file:
													each_relative_path = each_sub_path.split(each_path)[1] #c:/python27/lib/ - c:/python27/lib/bin/abc.pyc = bin/abc.pyc
													each_relative_hash = each_relative_path + hex(hash128( each_sub_file.read())) #WARNING- some files like thumbs.db constantly change, and therefore may cause an infinite upload loop. Need an ignore list.
													os_folder_hashes.append(each_relative_hash) #use relative path+filename and hash so that set does not ignore two idenitcal files in different sub-directories. Why? let's say bin/abc.pyc and usr/abc.pyc are identical, without the aforementioned system, a folder with just bin/abc.pyc will yield same hash as bin/abc.pyc + usr/abc.pyc, not good.
													#gevent.sleep()#print each_relative_hash
									each_file_name = os.path.split(each_path)[1]
									os_folder_hashes.sort()
									each_data = "".join(os_folder_hashes) #whole folder hash
								
								else: #single file
								
									display_file_names.append(each_file_name)
								
									with open(each_path, 'rb') as each_file: 
										each_file_name = os.path.split(each_path)[1]
										each_data = each_file.read()
								
								name_and_data_hash = os_file_hashes_new.append( each_file_name + format(hash128( each_data ), "x") + self.websocket_worker.ACCOUNT_SALT) #append the hash for this file #use filename and hash so that set does not ignore copies of two idenitcal files (but different names) in different directories
							
						except ZeroDivisionError:
							return #upload error clip
								
						os_file_hashes_new_set = set(os_file_hashes_new)

						if os_file_hashes_old_set != set(os_file_hashes_new):  #checks to make sure if name and file are the same

							for each_new_path in os_file_paths_new:
								try:
									if os.path.isdir(each_new_path):
										distutils.dir_util.copy_tree(each_new_path, os.path.join(TEMP_DIR, os.path.split(each_new_path)[1] ) )
									else:
										distutils.file_util.copy_file(each_new_path, TEMP_DIR )
								except distutils.errors.DistutilsFileError:
									pass
									
									
							print "\nRETURN!!!!\n"

							clip_hash_secure = hashlib.new("ripemd160", "".join(os_file_hashes_new) + self.websocket_worker.ACCOUNT_SALT).hexdigest() #MUST use list of files instead of set because set does not guarantee order and therefore will result in a non-deterministic hash 
							return __prepare_for_upload(
								file_names = os_file_names_new,
								clip_type = "files",
								clip_display = display_file_names,
								clip_hash_secure = clip_hash_secure, 
								compare_next = os_file_hashes_new_set
							)

				return (_return_if_text_or_url() or _return_if_bitmap() or _return_if_file() or None)
				
		except ZeroDivisionError:# TypeError:
			self.destroyBusyDialog()
			wx.MessageBox("Unable to access the clipboard. Another application seems to be locking it.", "Error")
			return None
			
	def setThrottle(self, speed="fast"):
		#the seconds before self.getClipboardContent() runs again
		#set to slow when dealing with files and bitmaps to prevent memory leaks
		if speed == "fast":
			milliseconds = 1111
		elif speed == "slow":
			milliseconds = 3333		
		self.throttle = milliseconds
		
	def runAsyncWorker(self): 
		##pdb.set_trace()
		#since reading/writing clipboard takes very little time, 
		#and since we must access clipboard in main loop, we should 
		#use async to modify a global variable (with a lock to prevent
		#race issues). wx.Yield simply switches back and forth
		#between mainloop and this coroutine.
		counter = 0
		while 1:
			if self.websocket_worker.KEEP_RUNNING and self.websocket_worker.ACCOUNT_SALT: #wait until user account salt arrives for encryption
				if counter % self.throttle == 0:# only run every second, letting it run without this restriction will call memory failure and high cpu
					#set clip global
					clip_content = self.getClipboardContent()
					if clip_content:
						#HOST_CLIP_CONTENT.set( clip_content['clip_text'] )#encode it to a data compatible with murmurhash and wxpython settext, which only expect ascii ie "heart symbol" to u/2339
						CLIENT_LATEST_CLIP.set( clip_content )  #NOTE SERVER_LATEST_CLIP.get() was not set
				counter += 1
			#resize panel
			self.panel.lst.checkColumns()
			#print "email %s | pass %s" % (self.TEMP_EMAIL, self.TEMP_PASS)
			gevent.sleep(0.001) #SLEEP HERE WILL CAUSE FILEEXPLORER AND UI TO SLOW
			wx.Yield() #http://goo.gl/6Jea2t
				

if __name__ == "__main__":
	app = wx.App(False)
	frame = Main()
	frame.Show(True)
	app.MainLoop()