import urlparse

def string_is_url(url):
	if len(url) < 2048 and len(url.split()) == 1: #make sure text is under 2048 (for performance), and make sure the text is continuous like a url should be
		if bool(urlparse.urlparse(url).scheme in ['http', 'https', 'ftp', 'ftps', 'bitcoin', 'magnet'] ): #http://stackoverflow.com/questions/25259134/how-can-i-check-whether-a-url-is-valid-using-urlparse
			return True
	return False