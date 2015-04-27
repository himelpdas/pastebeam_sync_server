from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import pylzma

def derive_key_and_iv(password, salt, key_length, iv_length): #http://stackoverflow.com/questions/16761458/how-to-aes-encrypt-decrypt-files-using-python-pycrypto-in-an-openssl-compatible
	d = d_i = ''
	while len(d) < key_length + iv_length:
		d_i = md5(d_i + password + salt).digest()
		d += d_i
	return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
	bs = AES.block_size
	salt = Random.new().read(bs - len('Salted__'))
	key, iv = derive_key_and_iv(password, salt, key_length, bs)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	out_file.write('Salted__' + salt)
	finished = False
	while not finished:
		chunk = in_file.read(1024 * bs)
		if len(chunk) == 0 or len(chunk) % bs != 0:
			padding_length = (bs - len(chunk) % bs) or bs
			chunk += padding_length * chr(padding_length)
			finished = True
		out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, out_file, password, key_length=32):
	bs = AES.block_size
	salt = in_file.read(bs)[len('Salted__'):]
	key, iv = derive_key_and_iv(password, salt, key_length, bs)
	cipher = AES.new(key, AES.MODE_CBC, iv)
	next_chunk = ''
	finished = False
	while not finished:
		chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
		if len(next_chunk) == 0:
			padding_length = ord(chunk[-1])
			chunk = chunk[:-padding_length]
			finished = True
			out_file.write(chunk)
			
			
from cStringIO import StringIO

def compress_encrypt(file_path):
	#https://github.com/fancycode/pylzma/blob/master/doc/USAGE.md
	#file_path = os.path.join(path, filename)
	compressor = pylzma.compressfile(file_path, eos=1)
	with open(file_path, 'w') as compressed_file:
		while True:
			tmp = compressor.read(1024)
			if not tmp:
				break
			compressed_file.write(tmp)
			
def clean_up():
	pass
			
def encrypt_compress(file_path):
	
