import wx, os

#see http://zetcode.com/wxpython/skeletons/ for tips

class MyListCtrl(wx.ListCtrl):
	def __init__(self, parent):
		super(MyListCtrl, self).__init__(parent,
		style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		# Add three columns to the list
		self.InsertColumn(0, "File", width=33  )
		self.InsertColumn(1, "From", wx.LIST_FORMAT_CENTER, width=89 )
		self.InsertColumn(2, "Type", wx.LIST_FORMAT_RIGHT, width=33, )
		self.InsertColumn(3, "Clipping (Double-click to copy)", width=333 )
		self.InsertColumn(4, "Date", wx.LIST_FORMAT_RIGHT, width=100 )
		
		self.resizeColumns(self) #ListCtrl instance also has method GetSize()
		
		self.Bind(wx.EVT_LIST_ITEM_SELECTED,
		self.onItemSelected)
		
		self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, #DOUBLE CLICK ##SEE PDF http://www.blog.pythonlibrary.org/2013/12/12/wxpython-objectlistview-double-click-items/
			self.onItemDoubleClick)
		
		self.Bind(wx.EVT_SIZE,
			self.resizeColumns)
		
		icon_file_names = os.listdir(os.path.normpath('images/16px/')) #https://github.com/teambox/Free-file-icons #https://www.iconfinder.com/icons/62659/cam_camera_image_lens_photo_icon#size=16
		self.icon_extensions = map(lambda each: ".%s"%os.path.splitext(each)[0], icon_file_names)
		images = [ os.path.normpath('images/16px/%s'%each) for each in icon_file_names ]
		self.il = wx.ImageList(16, 16)
		for i in images:
			self.il.Add(wx.Bitmap(i))
		self.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
		
		# Setup
		#data = [ ("row %d" % x,"value %d" % x,"data %d" % x) for x in range(10) ]
		#self.PopulateList(data)

	
	def resizeColumns(self, resize_event):
		width = resize_event.GetSize()[0]
		bleed = 25 #make width sligtly smaller so that vScroll can be hidden
		width = width - bleed

		col0 = width*0.05
		col1 = width*0.15
		col2 = width*0.10
		col3 = width*0.55
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
		val = self.getEventItem(event)
		frame = self.GetTopLevelParent()
		temp_dir = frame.TEMP_DIR
		file_name = val[0]
		clip_type = val[2]
		frame.setClipboardContent(file_name=file_name, clip_type=clip_type)
		
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
		
class MyPanel(wx.Panel):
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