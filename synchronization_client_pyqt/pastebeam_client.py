#--coding: utf-8 --

from gevent import monkey; monkey.patch_all()

#from PySide import QtGui, QtCore
from PySide.QtGui import *
from PySide import QtCore, QtGui

from parallel import *

from functions import *

import platform, distutils

class UIMixin(QtGui.QMainWindow): #handles menubar and statusbar, which qwidget did not do
	#SLOT IS A QT TERM MEANING EVENT
	def initUI(self):			   
		
		self.initPanel()
		self.initMenuBar()
		self.initStatusBar()
		
		self.setCentralWidget(self.main_widget)
		self.setGeometry(300, 300, 1024, 768)
		self.setWindowTitle('PasteBeam 1.0.0')	
		
		self.show()	
		
	def initPanel(self):
		#self.setLayout(grid)
		self.search = QLineEdit()
		
		self.list_widget  = QListWidget()
		list_widget_icon_size = QtCore.QSize(PixmapThumbnail.Px,PixmapThumbnail.Px)
		self.list_widget.setIconSize(list_widget_icon_size) #http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
		self.list_widget.setAlternatingRowColors(True) #http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors
		self.list_widget.doubleClicked.connect(self.onItemDoubleClickSlot)
		
		search_icon = QLabel() #http://www.iconarchive.com/show/super-mono-3d-icons-by-double-j-design/search-icon.html
		pmap = QPixmap("images/find.png")
		pmap = pmap.scaledToWidth(32, QtCore.Qt.SmoothTransformation)
		search_icon.setPixmap(pmap)
		
		#clipboard_icon = QLabel(self.ICON_HTML.format(name="clipboard",side=32))
		#grid = QGridLayout() #passing QApplication instance will set the QGridLayout to it, or use #self.setLayout(grid)
		#grid.setSpacing(10)
		
		vbox = QVBoxLayout()
		hbox_tool = QHBoxLayout()
		hbox_list = QHBoxLayout()
		
		pmap = QPixmap("images/up.png");
		icn = QIcon(pmap);
		btn1 = QPushButton("Up")
		btn1.setIcon(icn)
		
		pmap = QPixmap("images/down.png");
		icn = QIcon(pmap);
		btn2 = QPushButton("Down")
		btn1.setIcon(icn)
		
		hbox_tool.addWidget(btn1)
		hbox_tool.addWidget(btn2)
		
		hbox_tool.addStretch(1) #pushes widgets to the side, kind of like pull-right
		hbox_tool.addWidget(search_icon)
		hbox_tool.addWidget(self.search)
		
		hbox_list.addWidget(self.list_widget)
		vbox.addLayout(hbox_tool)
		vbox.addLayout(hbox_list)
		
		self.main_widget = QWidget() #used to be inherited by main, which will automatically display as a window, but now it is handled by setCentralWidget
		self.main_widget.setLayout(vbox) #http://www.qtcentre.org/threads/5648-How-do-I-add-a-QGridlayout-in-a-QMainwindow
		
	def initMenuBar(self):
	
		exitAction = QtGui.QAction(QtGui.QIcon("images/exit.png"), '&Exit', self)	#http://ubuntuforums.org/archive/index.php/t-724672.htmls	
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close) #exitAction.triggered.connect(QtGui.qApp.quit) #does not trigger closeEvent()
		
		menubar = self.menuBar()
		fileMenu = menubar.addMenu('&File')
		fileMenu.addAction(exitAction)
		
	def initStatusBar(self):
		
		self.sbar = sb = self.statusBar()
		
		self.status_lbl = lbl = QLabel("")
		
		sb.addPermanentWidget(lbl)
		
		self.status_icn = icn = QLabel("")
		
		sb.addPermanentWidget(icn)
		
		self.onSetStatusSlot(("Connecting", "connect"))
				
	def onSetStatusSlot(self, msg_icn):
		msg,icn = msg_icn
		self.status_lbl.setText("%s..."%msg.capitalize())
		
		pmap = QPixmap("images/{icn}".format(icn=icn))
		pmap = pmap.scaledToWidth(32, QtCore.Qt.SmoothTransformation) #antialiasing http://stackoverflow.com/questions/7623631/qt-antialiasing-png-resize
		self.status_icn.setPixmap(pmap)
		
		#events process once every x milliseconds, this forces them to process... or we can use repaint isntead
		qApp.processEvents() #http://stackoverflow.com/questions/4510712/qlabel-settext-not-displaying-text-immediately-before-running-other-method #the gui gets blocked, especially with file operations. DOCS: Processes all pending events for the calling thread according to the specified flags until there are no more events to process. You can call this function occasionally when your program is busy performing a long operation (e.g. copying a file).

class Main(WebsocketWorkerMixinForMain, UIMixin):

	TEMP_DIR = tempfile.mkdtemp()

	ICON_HTML = u"<html><img src='images/{name}.png' width={side} height={side} style='vertical-align:middle'></html>"
	
	HOST_NAME = u"{system} {release}".format(system = platform.system(), release = platform.release() ) #self.getLogin().get("device_name"),
	
	FILE_IGNORE_LIST = map(lambda each: each.upper(), ["desktop.ini","thumbs.db",".ds_store","icon\r",".dropbox",".dropbox.attr"])

	MAX_FILE_SIZE = 1024*1024*50
	
	SENDER_UUID = uuid.uuid4()
	
	def __init__(self, app):
		super(Main, self).__init__()
		
		self.app = app
		self.ws_worker = WebsocketWorker(self)
		self.ws_worker.incommingSignalForMain.connect(self.onIncommingSlot)
		self.ws_worker.newClipSignalForMain.connect(self.onSetNewClipSlot)
		self.ws_worker.statusSignalForMain.connect(self.onSetStatusSlot)
		self.ws_worker.start()
		
		self.initUI()
		self.setupClip()
			
	def setupClip(self):
		self.previous_hash = {}
		
		self.clipboard = self.app.clipboard() #clipboard is in the QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
		self.clipboard.dataChanged.connect(self.onClipChangeSlot) #datachanged is signal, doclip is slot, so we are connecting slot to handle signal
	"""	
	def _onClipChangeSlot(self):
		#self.status.setText(self.clipboard.text() or str(self.clipboard.pixmap()) )
		pmap = self.clipboard.pixmap()
		if pmap:
			#crop and reduce pmap size to fit square icon
			pmap = PixmapThumbnail(pmap)
			itm =  QListWidgetItem()
			itm.setIcon(QIcon(pmap.thumbnail))
			txt = "Copied Image / Screenshot ({w} x {h})".format(w=pmap.original_w, h=pmap.original_h )
		else:
			itm = QListWidgetItem()
			itm.setIcon(QIcon("images/text.png"))
			
			txt = cgi.escape(self.clipboard.text())
			txt = self.truncateTextLines(txt)
			txt = self.anchorUrls(txt)
		self.list_widget.addItem(itm) #or self.list_widget.addItem("some text") (different signature)
		custom_label = QLabel("<html><b>By Test on {timestamp}:</b><pre>{text}</pre></html>".format(timestamp = time.time(), text=txt ) )
		self.list_widget.setItemWidget(itm, custom_label )
		itm.setSizeHint( custom_label.sizeHint() )
		
		self.outgoingSignalForWorker.emit(txt)
		#self.status.setText(str(time.time()))
	"""
		
	def onClipChangeSlot(self):
		#test if identical
		#pmap = self.clipboard.pixmap()
		#text = self.clipboard.text()
		
		self.onSetStatusSlot(("scanning", "scan"))
		
		mimeData = self.clipboard.mimeData()
				
		if mimeData.hasImage():
			#image = pmap.toImage() #just like wxpython do not allow this to del, or else .bits() will crash
			image = mimeData.imageData()

			prev = self.previous_hash #image.bits() crashes with OneNote large image copy
			hash = format(hash128(image.bits()), "x") ##http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x #we want the large image out of memory asap, so just take a hash and gc collect the image
			
			PRINT("on clip change pmap", (hash,prev))
			if hash == prev:
				self.onSetStatusSlot(("image copied","good"))
				return
				
			#secure_hash = hashlib.new("ripemd160", hash + "ACCOUNT_SALT").hexdigest() #use pdkbf2 #to prevent rainbow table attacks of known files and their hashes, will also cause decryption to fail if file name is changed
			img_file_name = "%s.bmp"%hash
			img_file_path = os.path.join(self.TEMP_DIR, img_file_name)
			image.save(img_file_path) #change to or compliment upload
				
			pmap = QPixmap(image) #change to pixmap for easier image editing than Qimage
			pmap = PixmapThumbnail(pmap)
			
			device= QtCore.QBuffer() #is an instance of QIODevice, which is accepted by image.save()
			pmap.thumbnail.save(device, "PNG") # writes image into the in-memory container, rather than a file name
			bytearray = device.data() #get the buffer itself
			bytestring = bytearray.data() #copy the full string
			
			text = "Copied Image or Screenshot\n\n{w} x {h} Pixels\n{mp} Megapixels\n{mb} Megabytes".format(w=pmap.original_w, h=pmap.original_h, mp="%d.02"%(pmap.original_w*pmap.original_h/1000000.0), mb="%d.1"%(pmap.original_w*pmap.original_h*3/1024**2) )
			clip_display = dict(
				text=Binary(text), 
				thumb = Binary(bytestring)  #Use BSON Binary to prevent UnicodeDecodeError: 'utf8' codec can't decode byte 0xeb in position 0: invalid continuation byte
			)
			
			prepare = dict(
				file_names = [img_file_name],
				clip_display = clip_display,
				clip_type = "screenshot",
			)
		elif mimeData.hasHtml():
			html = mimeData.html().encode("utf8")
			text = (mimeData.text() or "<Rich Text Data>").encode("utf8")
			
			prev = self.previous_hash
			
			hash = format(hash128(html), "x")
			
			PRINT("on clip change html", (hash,prev))
			if hash == prev:
				self.onSetStatusSlot(("data copied","good"))
				return
			
			preview = cgi.escape(text) #crashes with big data
			preview = self.truncateTextLines(preview)
			preview = self.anchorUrls(preview)
						
			html_file_name = "%s.json"%hash
			html_file_path = os.path.join(self.TEMP_DIR,html_file_name)
			
			with open(html_file_path, 'w') as html_file:
				html_and_text = json.dumps({"html_and_text":{
					"html":html,
					"text":text
				}})
				html_file.write(html_and_text)
			
			prepare = dict(
				file_names = [html_file_name],
				clip_display = preview,
				clip_type = "html",
			)
			
		elif mimeData.hasText():
		
			original = mimeData.text().encode("utf8")
			
			print original
			
			prev = self.previous_hash
			
			hash = format(hash128(original), "x")
			
			PRINT("on clip change text", (hash,prev))
			if hash == prev:
				self.onSetStatusSlot(("text copied","good"))
				return
			
			preview = cgi.escape(original) #prevent html from styling in qlabel
			preview = self.truncateTextLines(preview)
			preview = self.anchorUrls(preview)
						
			text_file_name = "%s.txt"%hash
			text_file_path = os.path.join(self.TEMP_DIR,text_file_name)
			
			with open(text_file_path, 'w') as text_file:
				text_file.write(original)
			
			prepare = dict(
				file_names = [text_file_name],
				clip_display = preview,
				clip_type = "text",
			)

		elif mimeData.hasUrls():
			is_files = []
			for each in mimeData.urls():
				is_files.append(each.isLocalFile())
			if not (is_files and all(is_files) ):
				return
				
			PRINT("is files", True)

			os_file_paths_new = []
			
			for each in self.clipboard.mimeData().urls():
				#PRINT("path", each.toString().encode())
				each_path = each.path()[(1 if os.name == "nt" else 0):] #urls() returns /c://...// in windows, [1:] removes the starting /, not sure how this will affect *NIXs
				if os.name=="nt":
					each_path = each_path.encode(sys.getfilesystemencoding()) #windows uses mbcs encoding, not utf8 like *nix, so something like a chinese character will result in file operations raising WindowsErrors #http://stackoverflow.com/questions/10180765/open-file-with-a-unicode-filename
				standardized_path = os.path.abspath(each_path) #abspath is needed to bypass symlinks in *NIX systems, also guarantees slashes are correct (C:\\...) for windows
				os_file_paths_new.append(standardized_path)
			
			os_file_paths_new.sort()
			
			try:
				os_file_sizes_new = map(lambda each_os_path: getFolderSize(each_os_path, max=self.MAX_FILE_SIZE) if os.path.isdir(each_os_path) else os.path.getsize(each_os_path), os_file_paths_new)
			except ZeroDivisionError:
				PRINT("failure",213)
				return
			
			if sum(os_file_sizes_new) > self.MAX_FILE_SIZE:
				#self.sb.toggleStatusIcon(msg='Files not uploaded. Maximum files size is 50 megabytes.', icon="bad")
				self.onSetStatusSlot(("Files bigger than 50MB","warn"))
				PRINT("failure",218)
				return #upload error clip
							
			os_file_hashes_new = set([])
			
			os_file_names_new = []
			display_file_names =[]
			
			for each_path in os_file_paths_new:
			
				each_file_name = os.path.split(each_path)[1]
			
				os_file_names_new.append(each_file_name)
				
				if os.path.isdir(each_path):
				
					display_file_names.append(each_file_name+" folder (%s inside)"%len(os.listdir(each_path))+"._folder")
				
					os_folder_hashes = []
					for dirName, subdirList, fileList in os.walk(each_path, topdown=False):
						#subdirList = filter(...) #filer out any temp or hidden folders
						for fname in fileList:
							if fname.upper() not in self.FILE_IGNORE_LIST: #DO NOT calculate hash for system files as they are always changing, and if a folder is in clipboard, a new upload may be initiated each time a system file is changed
								each_sub_path = os.path.join(dirName, fname)
								with open(each_sub_path, 'rb') as each_sub_file:
									each_relative_path = each_sub_path.split(each_path)[1] #c:/python27/lib/ - c:/python27/lib/bin/abc.pyc = bin/abc.pyc
									each_relative_hash = each_relative_path + hex(hash128( each_sub_file.read())) #WARNING- some files like thumbs.db constantly change, and therefore may cause an infinite upload loop. Need an ignore list.
									os_folder_hashes.append(each_relative_hash) #use relative path+filename and hash so that set does not ignore two idenitcal files in different sub-directories. Why? let's say bin/abc.pyc and usr/abc.pyc are identical, without the aforementioned system, a folder with just bin/abc.pyc will yield same hash as bin/abc.pyc + usr/abc.pyc, not good.
									
					each_file_name = os.path.split(each_path)[1]
					os_folder_hashes.sort()
					each_data = "".join(os_folder_hashes) #whole folder hash
				
				else: #single file
				
					display_file_names.append(each_file_name)
				
					with open(each_path, 'rb') as each_file: 
						each_file_name = os.path.split(each_path)[1]
						each_data = each_file.read() #update status
				
				os_file_hashes_new.add(hash128(each_file_name) + hash128(each_data) ) #append the hash for this file #use filename and hash so that set does not ignore copies of two idenitcal files (but different names) in different directories #also hash filename as this can be a security issue when stored serverside
			
			checksum = format(sum(os_file_hashes_new), "x")					
			if self.previous_hash == checksum:  #checks to make sure if name and file are the same
				PRINT("failure",262)
				self.onSetStatusSlot(("File%s copied" % ("s" if len(os_file_names_new) > 1 else "") , "good"))
				return
			else:
				hash = checksum
							
			#copy files to temp. this is needed 
			for each_new_path in os_file_paths_new:
				try:
					if os.path.isdir(each_new_path):
						distutils.dir_util.copy_tree(each_new_path, os.path.join(self.TEMP_DIR, os.path.split(each_new_path)[1] ) )
					else:
						distutils.file_util.copy_file(each_new_path, self.TEMP_DIR )
				except distutils.errors.DistutilsFileError:
					#show error
					PRINT("failure",274)
					pass #MUST PASS since file may already be there.
			
			prepare = dict(
				file_names = os_file_names_new,
				clip_display = display_file_names,
				clip_type = "files",
			)

		else:
			self.onSetStatusSlot(("Clipping is incompatible","warn"))
			return	
		
		prepare["hash"]= hash
		self.outgoingSignalForWorker.emit(prepare)
		
		self.previous_hash = hash
		#image.destroy()
		
	def onSetNewClipSlot(self, new_clip):
		#only needed when user double clicks an item
			
		container_name = new_clip["container_name"]
		clip_type = new_clip["clip_type"]
		
		self.onSetStatusSlot(("decrypting", "unlock"))
		with encompress.Encompress(password = "nigger", directory = self.TEMP_DIR, container_name=container_name) as file_paths_decrypt:
			#print file_paths_decrypt
			
			mimeData = QtCore.QMimeData()
			
			if clip_type == "html":
			
				clip_file_path = file_paths_decrypt[0]
			
				with open(clip_file_path, 'r') as clip_file:
					
					clip_json = json.loads(clip_file.read()) #json handles encode and decode of UTF8
					
					clip_text = clip_json["html_and_text"]["text"] 
					clip_html = clip_json["html_and_text"]["html"]
					
					mimeData.setText(clip_text) #set text cannot automatically truncate html (or rich text tags) like with mimeData.text(). This is probably due to the operating system providing both text and html, and it's not Qt's concern. So I decided to store getText on json file and setText here.
					mimeData.setHtml(clip_html)
			

			if clip_type == "text":
			
				clip_file_path = file_paths_decrypt[0]
			
				with open(clip_file_path, 'r') as clip_file:
					
					clip_text = clip_file.read().decode("utf8") #http://stackoverflow.com/questions/6048085/python-write-unicode-text-to-a-text-file #needed to keep conistant hash, or else inifnite upload/update loop will occur
										
					mimeData.setText(clip_text)
					
					
			if clip_type == "screenshot":
			
				clip_file_path = file_paths_decrypt[0]
				
				image = QImage(clip_file_path)
								
				mimeData.setImageData(image)
				
			self.clipboard.setMimeData(mimeData)
			

			if clip_type == "files":
							
				urls = []
				
				for each_path in file_paths_decrypt:
					if os.name=="nt":
						each_path = each_path.replace("\\","/").replace("c:","C:")
						each_path = each_path.decode(sys.getfilesystemencoding()) #windows uses mbcs encoding, not utf8 like *nix, so something like a chinese character will result in file operations raising WindowsErrors #http://stackoverflow.com/questions/10180765/open-file-with-a-unicode-filename

					each_path = "file:///"+each_path
					
					QUrl = QtCore.QUrl()
					QUrl.setUrl(each_path)
					#QUrl.setPath(each_path)
					QUrl.toEncoded()
					urls.append(QUrl)
												
				PRINT("SETTING URLS", urls)
				mimeData.setUrls(urls)

				
			self.clipboard.setMimeData(mimeData)
			
		
	def onItemDoubleClickSlot(self, clicked):
		selected_row =  clicked.row()
		selected_item = self.list_widget.item(selected_row)
		
		current_item = self.list_widget.item(0)
		#current_clip = json.loads(current_item.data(QtCore.Qt.UserRole))
		
		selected_clip = json.loads(selected_item.data(QtCore.Qt.UserRole)) #http://stackoverflow.com/questions/25452125/is-it-possible-to-add-a-hidden-value-to-every-item-of-qlistwidget
		
		hash, prev = selected_clip["hash"], self.previous_hash
		
		if hash == prev:
			return
			
		del selected_clip['_id'] #this is an id from an old clip from server. must remove or else key error will occur on server when trying to insert new clip 
		if os.name=="nt" and selected_clip["clip_type"] == "files":
			selected_clip["file_names"] = map(lambda each_name: each_name.encode(sys.getfilesystemencoding()), selected_clip["file_names"]) #undo ms filename encoding back to ascii #http://stackoverflow.com/questions/10180765/open-file-with-a-unicode-filename
			selected_clip["clip_display"] = map(lambda each_name: each_name.encode(sys.getfilesystemencoding()), selected_clip["clip_display"])
		self.outgoingSignalForWorker.emit(selected_clip)
		
		self.previous_hash = hash #or else onClipChangeSlot will react and a duplicate new list item will occur.
		#PRINT("thumb on item.data", selected_clip["clip_display"])
		#self.setClip()
		
	@staticmethod
	def truncateTextLines(txt, max_lines=15):
		line_count = txt.count("\n")
		if line_count <= max_lines:
			return txt
		txt_split = txt.split("\n")
		line_diff = line_count-max_lines
		txt_split = txt_split[:max_lines] + ["<span style='color:red'>...", "... %s line%s not shown"%(line_diff, "s" if line_diff > 1 else ""), "...</span>"] + txt_split[-1:] #equal to [txt_split[-1]]
		txt = "\n".join(txt_split)
		return txt
	
	@staticmethod
	def anchorUrls(txt):
		found_urls = map(lambda each: each[0], GRUBER_URLINTEXT_PAT.findall(txt))
		for each_url in found_urls:
			txt = txt.replace(each_url, "<a href='{url}'>{url}</a>".format(url=each_url))
		return txt
		
	@staticmethod
	def decodeClipDisplay(clip):
		return (clip or '').decode("base64").decode("zlib").decode("utf-8", "replace")
	
	@staticmethod
	def encodeClipDisplay(clip):
		return (clip or '').encode("utf-8", "replace").encode("zlib").encode("base64") #MUST ENCODE in base64 before transmitting obsfucated data #null clip causes serious looping problems, put some text! Prevent setText's TypeError: String or Unicode type required 
		
	def closeEvent(self, event): #http://stackoverflow.com/questions/9249500/pyside-pyqt-detect-if-user-trying-to-close-window
		# if i don't terminate the worker thread, the app will crash (ex. windows will say python.exe stopped working)
		self.ws_worker.terminate() #http://stackoverflow.com/questions/1898636/how-can-i-terminate-a-qthread
		event.accept() #event.ignore() #stops from exiting
		
class PixmapThumbnail():
	Px = 56
	def __init__(self, original_pmap):
		self.original_pmap = original_pmap
		self.original_w = self.original_h = self.thumbnail = self.is_landscape = None
		self.pixmapThumbnail()

	def pixmapThumbnail(self):
		self.original_w = self.original_pmap.width()
		self.original_h = self.original_pmap.height()
		is_square = self.original_w==self.original_h
		if not is_square:
			smallest_side = min(self.original_w, self.original_h)
			longest_side = max(self.original_w, self.original_h)
			shift = longest_side / 4.0
			self.is_landscape = self.original_w > self.original_h
			if self.is_landscape:
				x = shift
				y = 0
			else:
				x = 0
				y = shift
			crop = self.original_pmap.copy(x, y, smallest_side, smallest_side) #PySide.QtGui.QPixmap.copy(x, y, width, height) #https://srinikom.github.io/pyside-docs/PySide/QtGui/QPixmap.html#PySide.QtGui.PySide.QtGui.QPixmap.copy
		else:
			crop = self.original_pmap
		self.thumbnail = crop.scaled(self.Px,self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv) #create mainloop
	ex = Main(app) #run widgets
	sys.exit(app.exec_())