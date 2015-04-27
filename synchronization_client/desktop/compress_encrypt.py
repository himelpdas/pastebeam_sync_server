from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
import pylzma

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
			
			
from cStringIO import StringIO
import random

BLOCK_SIZE = AES.block_size

def get_key_salt_and_iv(password, file_or_stream=None):
	if file_or_stream:
		iv = file_or_stream.read(BLOCK_SIZE)
		salt = file_or_stream.read(BLOCK_SIZE)
	else:
		rand_stream = Random.new()
		pre_iv = 'iv:'; iv = pre_iv+rand_stream.read(BLOCK_SIZE - len(pre_iv)) #IV prevents showing similarities in the 16 bit blocks of 2 files. Random iv isn't important just make sure iv is never used more than once. It is safe to keep with file.
		pre_salt ='salt:'; salt = pre_salt + rand_stream.read(BLOCK_SIZE - len(pre_salt)) #salt prevents dictionary (rainbow table) attacks to the password
	key = PBKDF2(password, salt = salt, dkLen = BLOCK_SIZE) #dkLen: The length of the desired key. Default is 16 bytes, suitable for instance for Crypto.Cipher.AES
	return (key, salt, iv)

def compress_encrypt(file_path, password="incredible1"):
	#https://github.com/fancycode/pylzma/blob/master/doc/USAGE.md
	#file_path = os.path.join(path, filename)
	with open(file_path,'rb') as raw_file:
	
		with open(file_path+".pastebeam", 'w') as container_file:
	
			compressor = pylzma.compressfile(raw_file, eos=1)
			
			read_bytes = BLOCK_SIZE*1024 #make sure it is divisible by block_size
				
			key, salt, iv = get_key_salt_and_iv(password)
					
			cipher = AES.new(key, AES.MODE_CBC, iv)
			
			container_file.write(iv)
			
			container_file.write(salt)
					
			while True:
				chunk = compressor.read(read_bytes)
				if not chunk:
					break
				if len(chunk) == 0 or len(chunk) % BLOCK_SIZE != 0: #end of file usually doesn't match block size so we must add padding
					padding_length = (BLOCK_SIZE - len(chunk) % BLOCK_SIZE) or BLOCK_SIZE #this is a trick to calculate EXACTLY how much extra padding is needed to make chunk divisible by AES.block_size (which is usually 16). For example the remainder is 30, so 30 % 16 = 14. We need 2 more pads to make the remainder divisible by 16, this can be calculated by 16-14 = 2.
					chunk += padding_length * chr(padding_length)
				container_file.write(cipher.encrypt(chunk)) #ALWAYS compress before encrypt, otherwise it is useless
			
def clean_up():
	pass