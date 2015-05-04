from hashlib import sha512
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
import tarfile
import gevent
import os

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
			
	
class Encompress():
	#Based heavily on #http://stackoverflow.com/questions/16761458/how-to-aes-encrypt-decrypt-files-using-python-pycrypto-in-an-openssl-compatible
	
	BLOCK_SIZE = AES.block_size
	READ_BYTES = BLOCK_SIZE*1024 #make sure it is divisible by self.BLOCK_SIZE
	
	def __init__(self,  password = "", directory = "", file_names = [], decrypt_file = None):
		self.file_names = file_names
		self.directory = directory
		self.password = password
		self.decrypt_file = decrypt_file
		
		self.salt = "".join(self.file_names)
		
		self.result = self.archive_path = self.container_path = self.iv = self.key = None
		
		
	def __enter__(self):
	
		if self.decrypt_file:
			self.grabIV()
			self.setKey()
			self.decrypt()
			self.extract()
		else:
			self.makeIV()
			self.setKey()
			self.compress()
			self.encrypt()

		return self.result

	def __exit__(self, type, value, traceback):
		
		for each_path in map(lambda each_name: os.path.join(self.directory, each_name), self.file_names):
			pass#os.remove(each_path)
			
		if self.archive_path:
			pass#os.remove(self.archive_path)
		
	def makeIV(self):
		pre_iv = 'iv:'
		rand = Random.new()
		self.iv = pre_iv + rand.read(self.BLOCK_SIZE - len(pre_iv)) #not needed since tarfile already is very random due to timestamp, but do for extra security #CBC requires a non-deterministic approach, in other words you can't recalculate the IV... deterministic is when you make a random-appearing IV, but it's not random indeed ie. using the file hash
		
	def grabIV(self):
		self.iv = self.decrypt_file.read(self.BLOCK_SIZE)
		print "\nIV:%s\n"%self.iv
		
	def setKey(self):
		self.key = PBKDF2(self.password, salt = self.salt, dkLen = self.BLOCK_SIZE) #dkLen: The length of the desired key. Default is 16 bytes, suitable for instance for Crypto.Cipher.AES
			
	def compress(self):
		self.archive_path = os.path.join(self.directory, self.file_names[0]+".tar.bz2") #TEMP
		tar = tarfile.open(self.archive_path, "w:bz2") #write mode in bz2 #compresslevel=9)
		for each_name in self.file_names:
			each_path =  os.path.join(self.directory, each_name)
			tar.add(each_path, arcname=each_name) #WARNING BY DEFAULT THE DIRECTORY PATH IS ADDED AS WELL, THEREFORE THE FINAL CONTAINER FILE's HASH WILL BE DIFFERENT, USE THIS SOLUTION #http://ubuntuforums.org/showthread.php?t=1699689
			gevent.sleep() #
		tar.close()

	def encrypt(self):

		with open(self.archive_path,'rb') as archive:
		
			self.container_path = self.archive_path+".pastebeam"
			
			with open(self.container_path, 'wb') as container_file:
																							
				cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
				
				container_file.write(self.iv)
										
				finished = False
				while not finished:
					chunk = archive.read(self.READ_BYTES)
					if len(chunk) == 0 or len(chunk) % self.BLOCK_SIZE != 0: #end of file usually doesn't match block size so we must add padding
						padding_length = (self.BLOCK_SIZE - len(chunk) % self.BLOCK_SIZE) or self.BLOCK_SIZE #this is a trick to calculate EXACTLY how much extra padding is needed to make chunk divisible by AES.self.BLOCK_SIZE (which is usually 16). For example the remainder is 30, so 30 % 16 = 14. We need 2 more pads to make the remainder divisible by 16, this can be calculated by 16-14 = 2.
						chunk += padding_length  * chr(padding_length)
						finished = True
					container_file.write(cipher.encrypt(chunk)) #ALWAYS compress before encrypt, otherwise it is useless
					
		self.result = self.container_path
		
	def decrypt(self):
		
			self.archive_path = os.path.abspath(self.decrypt_file.name).split(".pastebeam")[0] #http://stackoverflow.com/questions/1881202/getting-the-absolute-path-of-a-file-object
		
			print "\nDECRYPT ARCHIVR PATH %s\n"%self.archive_path
		
			with open(self.archive_path, 'wb') as archive:
		
				cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
				next_chunk = ''
				finished = False
				while not finished:
					chunk, next_chunk = next_chunk, cipher.decrypt(self.decrypt_file.read(self.READ_BYTES))
					if len(next_chunk) == 0:
						padding_length = ord(chunk[-1]) #BRILLIANT! DURING ENCRYPTION IT FILLS THE PADDING WITH A CHARACTER THAT ALSO REPRESENTS THE REMAINDER LENGTH. SO EX. padded with aaaaaa, ord(a) = 6, chr(6) = a 
						chunk = chunk[:-padding_length]
						finished = True
					archive.write(chunk)
		
	def extract(self):
		self.extract_path = os.path.join(self.directory,"extracted")
		tar = tarfile.open(self.archive_path)
		tar.extractall(path=self.extract_path)
		self.result = self.extract_path