from base_non_blocking_server import *
from bottle import run

@route('/stream')
def stream():
	#secret = request.query.secret
	
	client_latest_clip_hash = request.query.latest_clip_hash #latest one on request
	
	server_latest_clip_row = get_latest_clip_row()
	
	#print "last: %s latest: %s"%(last_clip_id,latest_clip)
	
	while client_latest_clip_hash == server_latest_clip_row["sig"]:
		sleep(0.25) #wait a second
		server_latest_clip_row = get_latest_clip_row() #new query
	
	yield json.dumps(server_latest_clip_row)
	
@route('/new_clip', method='POST') #@post('/new_clip')
def post_new_clip():
	try:
		new_clip_content = str(request.forms.get("new_clip_content"))
		new_clip_sig = hex(mmh3.hash(new_clip_content))
		new_clip_id = str(clips.insert(dict(content=new_clip_content, sig = new_clip_sig) ) )
		status = dict(
			new_clip_sig = new_clip_sig,
			new_clip_id = new_clip_id,
			success = True,
			#new_clip_content = new_clip_content #temp
		)
	except:
		status = dict(
			success = False, 
			reason = str(sys.exc_info()[0]) #http://goo.gl/cmtlsL
		)
	yield json.dumps(status)

run(host='0.0.0.0', port=8083, server='gevent')