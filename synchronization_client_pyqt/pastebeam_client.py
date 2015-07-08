# coding=utf8

from gevent import monkey; monkey.patch_all()

#from PySide import QtGui, QtCore
from PySide.QtGui import *
from PySide import QtCore

from parallel import *

class Main(QWidget, WebsocketWorkerMixin):

	temp_dir = tempfile.mkdtemp()

	icon_html = "<html><img src='images/{name}.png' width={side} height={side}></html>"
	
	def __init__(self, app):
		super(Main, self).__init__()
		
		self.app = app
		self.ws_worker = WebsocketWorker(self)
		self.ws_worker.incommingSignalForMain.connect(self.onIncommingSlot)
		self.ws_worker.start()
		
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
		self.previous_hash = {}
		
		self.clipboard = self.app.clipboard() #clipboard is in the QApplication class as a static (class) attribute. Therefore it is available to all instances as well, ie. the app instance.#http://doc.qt.io/qt-5/qclipboard.html#changed http://codeprogress.com/python/libraries/pyqt/showPyQTExample.php?index=374&key=PyQTQClipBoardDetectTextCopy https://www.youtube.com/watch?v=nixHrjsezac
		self.clipboard.dataChanged.connect(self.onClipChange) #datachanged is signal, doclip is slot, so we are connecting slot to handle signal
		
	def _onClipChange(self):
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
		
	def onClipChange(self):
		#test if identical
		pmap = self.clipboard.pixmap()
		
		if pmap:
			prev = self.previous_hash
			image = pmap.toImage() #just like wxpython do not allow this to del, or else .bits() will crash
			hash = format(hash128(image.bits()), "x") ##http://stackoverflow.com/questions/16414559/trying-to-use-hex-without-0x #we want the large image out of memory asap, so just take a hash and gc collect the image
			
			PRINT("on clip change", (hash,prev))
			if hash == prev:
				return
				
			pmap = PixmapThumbnail(pmap)
			image = pmap.thumbnail.toImage()
			text = "Copied Image / Screenshot ({w} x {h})".format(w=pmap.original_w, h=pmap.original_h )
			clip_display = dict(
				text=Binary(text), 
				thumb = Binary( bytes(image.bits() ) )  #Use Binary to prevent UnicodeDecodeError: 'utf8' codec can't decode byte 0xeb in position 0: invalid continuation byte
			)
			secure_hash = hashlib.new("ripemd160", hash + "ACCOUNT_SALT").hexdigest() #use pdkbf2 #to prevent rainbow table attacks of known files and their hashes, will also cause decryption to fail if file name is changed
			img_file_name = "%s.bmp"%secure_hash
			img_file_path = os.path.join(self.temp_dir, img_file_name)
			image.save(img_file_path) #change to or compliment upload
			
			prepare = dict(
				file_names = [img_file_name],
				clip_display = clip_display,
				clip_type = "screenshot",
				secure_hash = secure_hash, 
				host_name = "TEST",#self.getLogin().get("device_name"),
			)
			
			self.outgoingSignalForWorker.emit(prepare)
			self.previous_hash = hash
			#image.destroy()
		
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
		self.thumbnail = crop.scaled(48,48)
		
if __name__ == '__main__':
	
	app = QApplication(sys.argv) #create mainloop
	ex = Main(app) #run widgets
	sys.exit(app.exec_())