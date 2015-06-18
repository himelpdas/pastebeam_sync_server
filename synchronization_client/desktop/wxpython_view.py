import wx, os, json

import keyring #store passwords safely in the os

#see http://zetcode.com/wxpython/skeletons/ for tips

class MenuBarMixin():
	"""Cannot subclass wx.menu_bar directly, so make it a mixin"""
	
	file_item_id = wx.NewId() #wx.ID_EXIT #causes something to appear in statusbar
	toggle_item_id = wx.NewId()
	about_item_id = wx.NewId()
	login_item_id = wx.NewId()
	
	def doMenuBar(self):
		menu_bar = wx.MenuBar()
		
		file_menu = wx.Menu()
		toggle_item = file_menu.Append(self.toggle_item_id, 'Toggle')
		file_item = file_menu.Append(self.file_item_id, 'Quit')
		menu_bar.Append(file_menu, '&File')
				
		edit_menu = wx.Menu()
		login_item = edit_menu.Append(self.login_item_id, 'Login')
		menu_bar.Append(edit_menu, '&Edit')
		
		help_menu = wx.Menu()
		about_item = help_menu.Append(self.about_item_id, 'About')
		menu_bar.Append(help_menu, '&Help')
		
		self.SetMenuBar(menu_bar)

		self.Bind(wx.EVT_MENU, self.onQuit, file_item)
		self.Bind(wx.EVT_MENU, self.onToggleItem, toggle_item)
		self.Bind(wx.EVT_MENU, self.onAboutItem, about_item)
		self.Bind(wx.EVT_MENU, self.onLoginItem, login_item)
		
	def onToggleItem(self, e):
		if self.websocket_worker.KEEP_RUNNING == True:
			self.websocket_worker.KEEP_RUNNING = False
			self.sb.toggleSwitchIcon(on=False)
		else:
			self.websocket_worker.KEEP_RUNNING = True
			self.sb.toggleSwitchIcon(on=True)

	def onAboutItem(self, e):
		
		description = 'PasteBeam is a clipboard manager that syncs "Copy and Paste" across your devices.'

		licence = "PasteBeam is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version. PasteBeam is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with PasteBeam; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA"


		info = wx.AboutDialogInfo()
		#info.SetIcon(wx.Icon('hunter.png', wx.BITMAP_TYPE_PNG))
		info.SetIcon(wx.ArtProvider.GetIcon(wx.ART_FILE_SAVE))
		info.SetName('PasteBeam')
		info.SetVersion('1.0')
		info.SetDescription(description)
		info.SetCopyright('(C) 2015 Himel Das')
		info.SetWebSite('http://www.pastebeam.com')
		info.SetLicence(licence)
		info.AddDeveloper('Himel Das')
		info.AddDocWriter('Himel Das')
		info.AddArtist('Shogo Kadoya')
		info.AddTranslator('Himel Das')

		wx.AboutBox(info)
		
	def onLoginItem(self, e):
		
		self.login_dialog = MyLoginDialog(self)
		self.login_dialog.ShowModal()
		

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
		
		#self.Bind(wx.EVT_SIZE,
		#	self.resizeColumns)
		
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
			#if not wx.GetMouseState().LeftIsDown(): #left key is still up at the very last few resize events, so anything before left key down will be ignored, and resize of columns will be much faster
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
	
		frame = self.GetTopLevelParent()
		
		if not frame.websocket_worker.KEEP_RUNNING:
			wx.MessageBox(u"You must resume PasteBeam first!\n\nGo to File \u2192 Toggle or Edit \u2192 Login", "Error")
			return
	
		clicked_item = self.getEventItem(event)
		
		top_item_container_id = self.GetItemText(0, col=1)
		
		clicked_container_id = clicked_item[1]
		clicked_container_name = clicked_container_id + ".tar.gz.pastebeam"
		
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
		
		#self._addToolBar()
				
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
		
		self.ok_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_good.png'))
		self.toggleStatusIcon()
		
		self.on_icon = wx.StaticBitmap(self, bitmap=wx.Bitmap('images/16px/_on.png'))
		self.toggleSwitchIcon()
		
		self.Bind(wx.EVT_SIZE, self.OnSize)
		
	def toggleSwitchIcon(self, on = True):
		if on:
			self.on_icon.SetBitmap(wx.Bitmap('images/16px/_on.png'))
			#self.on_icon = wx.StaticBitmap(self, bitmap=wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE)) #http://ubuntuforums.org/showthread.php?t=1464292
		else:
			self.on_icon.SetBitmap(wx.Bitmap('images/16px/_off.png'))
			
		self.placeStatusIcon()
		
	def placeSwitchIcon(self):
		rect = self.GetFieldRect(2)
		self.on_icon.SetPosition((rect.x+10, rect.y+2))

	def toggleStatusIcon(self, msg = 'Sarting up...', icon = "good"):
		self.SetStatusText(msg, 1)
		self.ok_icon.SetBitmap(wx.Bitmap('images/16px/_%s.png'%icon))
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


class MyLoginDialog(wx.Dialog):
	"""
	Class to define login dialog
	"""
	def __init__(self, parent):
		"""Constructor"""
				
		wx.Dialog.__init__(self, parent, title="Login Info", size=(200,150))
		
		self.frame = parent

		# email info
		email_sizer = wx.BoxSizer(wx.HORIZONTAL)
 
		email_lbl = wx.StaticText(self, label="       Email:")
		email_sizer.Add(email_lbl, 0, wx.ALL|wx.CENTER, 5)
		self.email = wx.TextCtrl(self)
		email_sizer.Add(self.email, 0, wx.ALL, 5)
 
		# pass info
		p_sizer = wx.BoxSizer(wx.HORIZONTAL)
 
		p_lbl = wx.StaticText(self, label="Password:")
		p_sizer.Add(p_lbl, 0, wx.ALL|wx.CENTER, 5)
		self.password = wx.TextCtrl(self, style=wx.TE_PASSWORD|wx.TE_PROCESS_ENTER)
		p_sizer.Add(self.password, 0, wx.ALL, 5)
 
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		main_sizer.Add(email_sizer, 0, wx.ALL, 5)
		main_sizer.Add(p_sizer, 0, wx.ALL, 5)
 
		btn = wx.Button(self, label="Save")
		btn.Bind(wx.EVT_BUTTON, self.onSave)
		main_sizer.Add(btn, 0, wx.ALL|wx.CENTER, 5)
 
		self.SetSizer(main_sizer)
		
	def onSave(self, e):
		
		keyring.set_password("pastebeam","login",json.dumps({"email":self.email.GetValue(), "password":self.password.GetValue()}))
		#put in method\/
		self.frame.websocket_worker.KEEP_RUNNING = True
		self.frame.websocket_worker.FORCE_RECONNECT = True #this is needed to refresh the password on server
		self.frame.sb.toggleSwitchIcon(on=True)
		
		self.Destroy()