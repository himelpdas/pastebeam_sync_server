import wx, os

#see http://zetcode.com/wxpython/skeletons/ for tips

class MyListCtrl(wx.ListCtrl):
	def __init__(self, parent):
		super(MyListCtrl, self).__init__(parent,
		style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		# Add three columns to the list
		self.InsertColumn(0, "Data", wx.LIST_FORMAT_RIGHT, )#width=44, )
		self.InsertColumn(1, "ID")
		self.InsertColumn(2, "Preview (Double-click to copy into clipboard)", )#width=333 )
		self.InsertColumn(3, "From", wx.LIST_FORMAT_CENTER,)# width=89 )
		self.InsertColumn(4, "Date", wx.LIST_FORMAT_RIGHT,)# width=100 )
		
		self.resizeColumns(self) #ListCtrl instance also has method GetSize()
		
		self.previous_size = self.GetSize()
		
		#self.Bind(wx.EVT_LIST_ITEM_SELECTED,
		#self.onItemSelected)
		
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, #DOUBLE CLICK ##SEE PDF http://www.blog.pythonlibrary.org/2013/12/12/wxpython-objectlistview-double-click-items/
			self.onItemDoubleClick)
		
		self.Bind(wx.EVT_SIZE,
			self.resizeColumns)
		
		#icon_file_names = os.listdir(os.path.normpath('images/16px/')) #WARNING, USE AN ACTUAL LIST AS OS LEVEL CRAP LIKE Thumbs.db WILL BREAK PROGRAM #https://github.com/teambox/Free-file-icons #https://www.iconfinder.com/icons/62659/cam_camera_image_lens_photo_icon#size=16
		icon_file_names = ['aac.png', 'ai.png', 'aiff.png', 'avi.png', 'bmp.png', 'c.png', 'cpp.png', 'css.png', 'dat.png', 'dmg.png', 'doc.png', 'dotx.png', 'dwg.png', 'dxf.png', 'eps.png', 'exe.png', 'flv.png', 'gif.png', 'h.png', 'hpp.png', 'html.png', 'ics.png', 'iso.png', 'java.png', 'jpg.png', 'js.png', 'key.png', 'less.png', 'mid.png', 'mp3.png', 'mp4.png', 'mpg.png', 'odf.png', 'ods.png', 'odt.png', 'otp.png', 'ots.png', 'ott.png', 'pdf.png', 'php.png', 'png.png', 'ppt.png', 'psd.png', 'py.png', 'qt.png', 'rar.png', 'rb.png', 'rtf.png', 'sass.png', 'scss.png', 'sql.png', 'tga.png', 'tgz.png', 'tiff.png', 'txt.png', 'wav.png', 'xls.png', 'xlsx.png', 'xml.png', 'yml.png', 'zip.png', '_bitmap.png', '_blank.png', '_clip.png', '_folder.png', '_error.png', '_link.png', '_multi.png', '_page.png']
		self.icon_extensions = map(lambda each: ".%s"%os.path.splitext(each)[0], icon_file_names)
		images = [ os.path.normpath('images/48px/%s'%each) for each in icon_file_names ]
		self.il = wx.ImageList(48, 48)
		for i in images:
			self.il.Add(wx.Bitmap(i))
		self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
		
		# Setup
		#data = [ ("row %d" % x,"value %d" % x,"data %d" % x) for x in range(10) ]
		#self.PopulateList(data)
		
	def checkColumns(self):
		if self.previous_size != self.GetSize():
			print "\nRESIZE: p:%s n:%s\n"%(self.previous_size, self.GetSize())
			self.resizeColumns(self)
			self.previous_size = self.GetSize()
	
	def resizeColumns(self, resize_event):
		width = resize_event.GetSize()[0]
		bleed = 25 #make width sligtly smaller so that vScroll can be hidden
		width = width - bleed

		col0 = width*0.10
		col1 = width*0.00
		col2 = width*0.60
		col3 = width*0.15
		col4 = width*0.15

		colwidths = [col0, col1, col2, col3, col4]
		
		for number, width in enumerate(colwidths):
			if not wx.GetMouseState().LeftIsDown(): #left key is still up at the very last few resize events, so anything before left key down will be ignored, and resize of columns will be much faster
				wx.CallLater(0.01, lambda number=number, width=width: self.SetColumnWidth(number, width)) #wx calllater for smoother operation #https://groups.google.com/forum/#!topic/wxpython-users/tWiSDnbpWcM
	
	def PopulateList(self, data):
		"""Populate the list with the set of data. Data
		should be a list of tuples that have a value for each
		column in the list.
		[('hello', 'list', 'control'),]
		"""
		for item in data:
			self.Append(item)
		
	def onItemSelected(self, event):
		val = self.getEventItem(event)
		# Show what was selected in the frames status bar
		frame = self.GetTopLevelParent()
		frame.PushStatusText(
			' '.join(val[3].split()) #beautiful, get's rid of /n " " and "	" #http://stackoverflow.com/questions/4241757/python-django-how-to-remove-extra-white-spaces-tabs-from-a-string
		)
		
	def onItemDoubleClick(self, event):
	
		clicked_item = self.getEventItem(event)
		frame = self.GetTopLevelParent()
		
		top_item_container_id = self.GetItemText(0, col=1)
		
		clicked_container_id = clicked_item[1]
		clicked_container_name = clicked_container_id + ".tar.bz2.pastebeam"
		
		clicked_clip_type = clicked_item[0]
		
		#print "DCLICK %s - %s"%(clicked_container_name, top_item_container_name)
		
		if clicked_container_id != top_item_container_id:
		
			frame.showBusyDialog()

			frame.setClipboardContent(container_name=clicked_container_name, clip_type=clicked_clip_type)
			
		else:
			wx.MessageBox("This item is already in your clipboard!", "Info")
		
	def getEventItem(self, event):
		selected_row = event.GetIndex()
		val = list()
		for column in range(self.GetColumnCount() ):
			item = self.GetItem(selected_row, column)
			val.append(item.GetText())
		return val
		
	def ListCompareFunction(self, item1, item2):
		if item1 > item2:
			return -1
		elif item1 < item2:
			return 1
		elif item1 ==  item2:
			return 0
		
class MyPanel(wx.Panel): #http://zetcode.com/wxpython/gripts/
	def __init__(self, parent):
		super(MyPanel, self).__init__(parent)
		
		self.vsizer_main = wx.BoxSizer(wx.VERTICAL)
		
		self._addToolBar()
				
		self._addMyListCtrl()
		
		self.SetSizer(self.vsizer_main)
		
	def _addToolBar(self):
		self.hsizer_toolbar = wx.BoxSizer(wx.VERTICAL)
		
		button = wx.Button(self, -1, "Add device")
		self.hsizer_toolbar.Add(button, 1, wx.TOP | wx.LEFT | wx.RIGHT, 20)
		
		self.vsizer_main.Add(self.hsizer_toolbar)
		
	def _addMyListCtrl(self):
		# Attributes
		self.lst = MyListCtrl(self)
		# Layout
		self.vsizer_main.Add(self.lst, 1, wx.EXPAND | wx.ALL, 20)
		# Event Handlers
		
class MyStatusBar(wx.StatusBar): #http://zetcode.com/wxpython/gripts/
	
	def __init__(self, parent):
		super(MyStatusBar, self).__init__(parent)

		self.SetFieldsCount(3)
		self.SetStatusWidths([17, -1, 17])
		
		self.toggleStatusIcon()
		self.toggleSwitchIcon()
		
		self.Bind(wx.EVT_SIZE, self.OnSize)
		
	def toggleSwitchIcon(self, on = True):
		if on:
			self.on_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_on.png'))
		else:
			self.on_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_off.png'))
			
		self.placeStatusIcon()
		
	def placeSwitchIcon(self):
		rect = self.GetFieldRect(2)
		self.on_icon.SetPosition((rect.x+5, rect.y+1))

	def toggleStatusIcon(self, msg = 'Sarting up...', ok = True):
		self.SetStatusText(msg, 1)
		
		if ok:
			self.ok_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_good.png'))
		else:
			self.ok_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_bad.png'))
			
		"""
		self.ok_icon = wx.StaticBitmap(self)
		if ok == True:
			self.ok_icon.SetBitmap(wx.Bitmap('images/16px/_good.png'))
		else:
			self.ok_icon.SetBitmap(wx.Bitmap('images/16px/_bad.png'))
		"""
		
		self.placeStatusIcon()
		
	def placeStatusIcon(self):
		rect = self.GetFieldRect(0)
		self.ok_icon.SetPosition((rect.x+5, rect.y+1))
		
	def placeIcons(self):
		self.placeStatusIcon()
		self.placeSwitchIcon()

	def OnSize(self, e):
				
		e.Skip()
		self.placeIcons()