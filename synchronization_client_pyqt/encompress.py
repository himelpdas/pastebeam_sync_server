from hashlib import sha512
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
import tarfile
import time, os, hashlib, uuid

"""
def derive_key_and_iv(password, salt, key_length, iv_length): #http://stackoverflow.com/questions/16761458/how-to-aes-encrypt-decrypt-files-using-python-pycrypto-in-an-openssl-compatible
	d = d_i = ''
	while len(d) < key_length + iv_length:
		d_i = md5(d_i + password + salt).digest()
		d += d_i
	return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
	BLOCK_SIZE = AES.block_size
	salt = Random.new().read(BLOCK_SIZE - len('Salted__'))
	key, iv = derive_key_and_iv(password, salt, key_length, BLOCK_SIZE)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	out_file.write('Salted__' + salt)
	finished = False
	while not finished:
		chunk = in_file.read(1024 * BLOCK_SIZE)
		if len(chunk) == 0 or len(chunk) % BLOCK_SIZE != 0:
			padding_length = (BLOCK_SIZE - len(chunk) % BLOCK_SIZE) or BLOCK_SIZE
			chunk += padding_length * chr(padding_length)
			finished = True
		out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, out_file, password, key_length=32):
	BLOCK_SIZE = AES.block_size
	salt = in_file.read(BLOCK_SIZE)[len('Salted__'):]
	key, iv = derive_key_and_iv(password, salt, key_length, BLOCK_SIZE)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	next_chunk = ''
	finished = False
	while not finished:
		chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * BLOCK_SIZE))
		if len(next_chunk) == 0:
			padding_length = ord(chunk[-1])
			chunk = chunk[:-padding_length]
			finished = True
			out_file.write(chunk)
"""

def timeit(method):

	def timed(*args, **kw):
		ts = time.time()
		result = method(*args, **kw)
		te = time.time()

		print '%r (%r, %r) %2.2f sec' % \
			  (method.__name__, args, kw, te-ts)
		return result

	return timed		
	
class Encompress():
	#Based heavily on #http://stackoverflow.com/questions/16761458/how-to-aes-encrypt-decrypt-files-using-python-pycrypto-in-an-openssl-compatible
	
	BLOCK_SIZE = AES.block_size
	READ_BYTES = BLOCK_SIZE*1024 #make sure it is divisible by self.BLOCK_SIZE
	
	def __init__(self,  password = "", directory = "", file_names_encrypt = [], container_name = None):
		if container_name:
			self.mode = "decrypt"
			self.container_name = container_name
			self.archive_name = container_name.split(".pastebeam")[0]
		else:
			self.mode = "encrypt"
			self.archive_id = str(uuid.uuid4())
			self.archive_name = self.archive_id + ".tar.gz"
			archive_ext= ".pastebeam"
			self.container_name = self.archive_name + archive_ext

		self.archive_path = os.path.join(directory, self.archive_name) #TEMP
		self.container_path = os.path.join(directory, self.container_name)
				
		self.file_names = file_names_encrypt
		self.directory = directory
		self.password = password
				
		self.result = self.iv = self.key = None
		
		
	def __enter__(self):
	
		if self.mode=="decrypt":
			self.grabIV()
			self.setKey()
			self.decrypt()
			self.extract()
		elif self.mode=="encrypt":
			self.makeIV()
			self.setKey()
			self.compress()
			self.encrypt()

		return self.result

	def __exit__(self, type, value, traceback):
		
		#for each_path in map(lambda each_name: os.path.join(self.directory, each_name), self.file_names_encrypt):
		#	pass#os.remove(each_path)
			
		if self.archive_path:
			os.remove(self.archive_path)
		
	@timeit
	def makeIV(self):
		pre_iv = 'iv:'
		pre_salt = 'salt:'
		rand = Random.new() #iv should be different for every file, so that patterns can't be seen in 2 identical files. This is apposed to salt, where the salt can be set once for one password (to prevent rainbow tables)
		self.iv = pre_iv + rand.read(self.BLOCK_SIZE - len(pre_iv)) #not needed since tarfile already is very random due to timestamp, but do for extra security #CBC requires a non-deterministic approach, in other words you can't recalculate the IV... deterministic is when you make a random-appearing IV, but it's not random indeed ie. using the file hash
		self.salt = pre_salt + rand.read(self.BLOCK_SIZE - len(pre_salt)) #not needed since tarfile already is very random due to timestamp, but do for extra security #CBC requires a non-deterministic approach, in other words you can't recalculate the IV... deterministic is when you make a random-appearing IV, but it's not random indeed ie. using the file hash
		
	@timeit
	def grabIV(self):		
		self.file_decrypt  = open(self.container_path, "rb")
		self.iv = self.file_decrypt.read(self.BLOCK_SIZE)
		self.salt = self.file_decrypt.read(self.BLOCK_SIZE)
		print "\nIV:%s\n"%self.iv
	
	@timeit
	def setKey(self): #salt isn't needed as IV scrambles aes, but pbkdf2 will slow down bruteforce plain key attacks by magnitudes
		self.key = PBKDF2(self.password, salt = self.salt, dkLen = self.BLOCK_SIZE) #dkLen: The length of the desired key. Default is 16 bytes, suitable for instance for Crypto.Cipher.AES
			
	@timeit
	def compress(self):
		#file_names = self.file_names_encrypt[0] #redundant / dry here. seems like cliphash secure is good enough
		#archive_id  = hashlib.new("ripemd160", "".join(file_names) + files_hash ).hexdigest()
		
		tar = tarfile.open(self.archive_path, "w:gz", encoding="utf8") #write mode in gz #compresslevel=9)
		for each_name in self.file_names:
			each_path =  os.path.join(self.directory, each_name)
			tar.add(each_path, arcname=each_name) #WARNING BY DEFAULT THE DIRECTORY PATH IS ADDED AS WELL, THEREFORE THE FINAL CONTAINER FILE's HASH WILL BE DIFFERENT, USE THIS SOLUTION #http://ubuntuforums.org/showthread.php?t=1699689
			#gevent.sleep() #
		tar.close()

	@timeit
	def encrypt(self):

		with open(self.archive_path,'rb') as archive:
			
			with open(self.container_path, 'wb') as container_file:
			
				cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
				
				container_file.write(self.iv)
				container_file.write(self.salt)
										
				finished = False
				while not finished:
					chunk = archive.read(self.READ_BYTES)
					if len(chunk) == 0 or len(chunk) % self.BLOCK_SIZE != 0: #end of file usually doesn't match block size so we must add padding
						padding_length = (self.BLOCK_SIZE - len(chunk) % self.BLOCK_SIZE) or self.BLOCK_SIZE #this is a trick to calculate EXACTLY how much extra padding is needed to make chunk divisible by AES.self.BLOCK_SIZE (which is usually 16). For example the remainder is 30, so 30 % 16 = 14. We need 2 more pads to make the remainder divisible by 16, this can be calculated by 16-14 = 2.
						chunk += padding_length  * chr(padding_length)
						finished = True
					container_file.write(cipher.encrypt(chunk)) #ALWAYS compress before encrypt, otherwise it is useless
					#gevent.sleep()
					
		self.result = self.container_name
		
	@timeit
	def decrypt(self):
			
		#self.archive_path = self.file_path_decrypt.split(".pastebeam")[0] # 			self.archive_path = os.path.abspath(self.file_decrypt.name).split(".pastebeam")[0] #http://stackoverflow.com/questions/1881202/getting-the-absolute-path-of-a-file-object
	
		print "DECRYPT ARCHIVR PATH %s"%self.archive_path
	
		with open(self.archive_path, 'wb') as archive:
	
			cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
			next_chunk = ''
			finished = False
			while not finished:
				chunk, next_chunk = next_chunk, cipher.decrypt(self.file_decrypt.read(self.READ_BYTES))
				if len(next_chunk) == 0:
					padding_length = ord(chunk[-1]) #BRILLIANT! DURING ENCRYPTION IT FILLS THE PADDING WITH A CHARACTER THAT ALSO REPRESENTS THE REMAINDER LENGTH. SO EX. padded with aaaaaa, ord(a) = 6, chr(6) = a 
					chunk = chunk[:-padding_length]
					finished = True
				archive.write(chunk)
				#gevent.sleep()
		
	@timeit
	def extract(self):
		#self.extract_path = os.path.join(self.directory,"extracted")
		print "\n\nArchive: %s\n\n"%self.archive_path
		tar = tarfile.open(self.archive_path)

		#The issue is the filenames in Tarfile.add() are encoded by default to sys.getfilesystemconding() (mbcs in windows), unless specified in encoding argument. There are two problems:
		#1) This is not cross-platform and will fail in *nix muchanines. 2) mbcs fails at decoding chinese characters, so ? will be stored in the tarfile instead of a chinese character. This causes an ioerror when tarfile attempts extractall since,  >>> u"\u9999".encode("mbcs") >>> "?"
		#the solution is to set encoding to "utf8" in tarfile, before any add(). The problem is windows cannot directly access utf8 encoded bytestring representations, so we must convert it back to system unicode (hence the decode)
		#Windows cannot handle unicode filenames, it uses its own representation
		def recover(name):
			#return unicode(name, 'utf-8')
			return name.decode("utf8") #decode back to unicode representation

		updated = []
		for m in tar.getmembers(): 
			print m.name
			m.name = recover(m.name)
			#print m.name
			updated.append(m)
		#http://superuser.com/questions/60379/how-can-i-create-a-zip-tgz-in-linux-such-that-windows-has-proper-filenames

		tar.extractall(path=self.directory, members = updated)
	
		root_file_and_folder_names = filter(lambda each_name: not "/" in each_name, tar.getnames()) #getnames alone returns folder cool.jpg ,48px, 48px/css.png, etc., we want 48px, and cool.jpg only
		self.result = map(lambda each_name: os.path.join(self.directory, each_name), root_file_and_folder_names )
		tar.close()