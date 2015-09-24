#TODO get sentry to track stacktraces
from gevent import monkey; monkey.patch_all() #declare BEFORE all imports

from functions import *

from gevent.event import AsyncResult
#from gevent.queue import Queue
from collections import deque

import uuid, time

from bottle import Bottle, static_file
app = Bottle()

if os.name=="nt":
	UPLOAD_DIR="C:\\Users\\Himel\\Desktop\\test\\uploads"
else:
	UPLOAD_DIR="/home/das/Projects/junk"
	
def PRINT(label, data):
	print "\n%s: %s"%(label.capitalize(), data)

@app.route('/echo')
def test_async_websocket():
	wsock = request.environ.get('wsgi.websocket')
	if not wsock:
		abort(400, 'Expected WebSocket request.')

	while True:
		try:	
			message = wsock.receive()
			#sleep(8)
			wsock.send(message)
		except WebSocketError:
			break
			
def addClipAndDeleteOld(data, system, owner_id):
	data["owner_id"]=owner_id
	data["system"]=system
	data['timestamp_server'] = time.time()
	id = bool(MONGO_CLIPS.insert_one(data).inserted_id)

	#find old crap
	tmp_free_user_limit = 5
	old = MONGO_CLIPS.find({
		"system":system,
		"owner_id":owner_id,
	}).sort('_id',pymongo.DESCENDING)[tmp_free_user_limit:]
	
	#delete old crap
	MONGO_CLIPS.delete_many({"_id":{'$in': map(lambda each: each["_id"], old) }  }   )
	
	return id
			
def incommingGreenlet(wsock, timeout, checkLogin, OUTGOING_QUEUE): #these seem to run in another namespace, you must pass them global or inner variables
	
	for second in timeout: #Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem
	
		received = wsock.receive()
		
		if not received:
			raise WebSocketError
			
		delivered = json.loads(received)
		
		question  = delivered['question']
		
		data = delivered['data']
		
		print delivered
		
		response = {"echo":delivered["echo"]}
		
		success = reason = None
		
		MY_ACCOUNT = checkLogin()["found"]
		MY_ID = MY_ACCOUNT["_id"] #need to keep this the most updated, incomming greenlet is ideal since it blocks and will reduce db hits
		MY_EMAIL = MY_ACCOUNT["email"].lower()
		MY_FIRST_NAME, MY_LAST_NAME = MY_ACCOUNT["first_name"].capitalize(), MY_ACCOUNT["last_name"].capitalize()
		
		if question == "Invite?":
			
			his_email = data["email"].lower()
												
			previous_invite = MONGO_INVITES.find_one({"owner_id":MY_ID, "to":his_email})
			
			try:
			
				assert MY_EMAIL != his_email, "Cannot send an invite to yourself! (Error 88)"
			
				if previous_invite:
					now = datetime.datetime.utcnow()
					delta =  now - previous_invite["date"]
					days = delta.days
					
					assert days >=2, "You can send an invite to this person once every 48 hours! (Error 95)"
					#delete old friend request
					MONGO_INVITES.delete_one({"_id":previous_invite["_id"], "owner_id":MY_ID}) #owner_id not needed as this _id is not known by attacker, however it may be needed for indexing

				MONGO_INVITES.insert_one({"owner_id":MY_ID, "to":his_email, "used":False, "date":datetime.datetime.utcnow()})
				
				his_email = his_email
				his_account = MONGO_ACCOUNTS.find_one({"email":his_email})
				if his_account:
					his_id = his_account["_id"]
					his_first_name, his_last_name = his_account["first_name"].capitalize(), his_account["last_name"].capitalize()
					
					reason = "{first_name} {last_name} sent you a contact invite.".format(first_name = MY_FIRST_NAME, last_name = MY_LAST_NAME)
					
					data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(), u'clip_type': u'invite', "session_id":str(uuid.uuid4()), "hash":str(uuid.uuid4()), u'host_name': MY_EMAIL} #uuid as a dummy hash
					
					addClipAndDeleteOld(data, "alert", his_id)
					
					reason = "You sent {first_name} {last_name} a contact invite.".format(first_name = his_first_name, last_name = his_last_name)

					data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(), u'clip_type': u'notify', "session_id":str(uuid.uuid4()), "hash":str(uuid.uuid4()), u'host_name': his_email} #uuid as a dummy hash
						
					addClipAndDeleteOld(data, "alert", MY_ID)
				else:
					pass #EMAIL THIS PERSON TO JOIN
				
				success = True

			except AssertionError as e:
				success = False
				reason = e[0]
		
			response.update(dict(
				answer="Contacts!",
				data = {
					"success":success,
					"reason":reason
				}
			))

		if question == "Accept?":
		
			his_email = data["email"].lower()
			
			his_account = MONGO_ACCOUNTS.find_one({"email":his_email})
			
			try:
				assert his_email, "Malformed request. (Error 126)"
				assert his_account, "Invite sender not found. Maybe acccount was deleted? (Error 127)"
					
				his_id = his_account["_id"]
					
				assert his_email != MY_EMAIL, "You cannot accept your own email. (Error 132)"
					
				#see if the email this user wants to add is in a corresponding invite
				previous_invite = MONGO_INVITES.find_one({"owner_id":his_id, "to":MY_EMAIL})
				
				assert previous_invite, "No invitation found from this user! (Error 152)"
				
				assert not previous_invite["used"], "Invitation had been already used. (Error 155)"

				def _addEmailToContacts(account, add_email):
					_id = account["_id"]
					contacts = list(set(account["contacts_list"] + [add_email] )  )
					MONGO_ACCOUNTS.update_one({"_id":_id}, {"$set":{"contacts_list" : contacts}}) #upsert True will update (with arg2 )if filter (arg1) not found
					
				_addEmailToContacts(MY_ACCOUNT, his_email)
				_addEmailToContacts(his_account, MY_EMAIL)
			
				reason = "{first_name} {last_name} accepted your contact invite!".format(first_name = his_account["first_name"].capitalize(), last_name = his_account["last_name"].capitalize() )
				data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(), u'clip_type': u'notify', "session_id":None, "hash":str(uuid.uuid4()), u'host_name': MY_EMAIL} #uuid as a dummy hash
				
				addClipAndDeleteOld(data, "alert", his_id)
			
				reason = "You accepted a contact invite from {first_name} {last_name}!".format(first_name = his_account["first_name"].capitalize(), last_name = his_account["last_name"].capitalize() )
				data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(), u'clip_type': u'notify', "session_id":None, "hash":str(uuid.uuid4()), u'host_name': his_email} #uuid as a dummy hash
				
				addClipAndDeleteOld(data, "alert", MY_ID)
				
				MONGO_INVITES.find_one_and_update({"_id":previous_invite["_id"]},{"$set":{"used":True}})
								
				success = True

			except AssertionError as e:
				success = False
				reason = e[0]
			
			response.update(dict(
				answer="Accept!",
				data = {
					"success":success,
					"reason":reason
				}
			))

		if question == "Contacts?":
			#IN PROGRESS

			try:
				modified_list = data["contacts_list"] #Modified list will ALWAYS be less than or equal to contacts, since the only way to add contacts is via invites

				contacts_list = sorted(MY_ACCOUNT["contacts_list"])

				if modified_list != None: # [] is valid, None is just get

					assert all( validators.email(each_email) for each_email in modified_list ), "An email failed validation. (Error 206)" #this is a setter, so make sure it passes validation				

					assert set(modified_list).issubset(contacts_list), "Illegal operation. (Error 209)" #make sure user's modified_list does not have anything that's not in original contacts list. IE hacker may want to add someone else's email who did not send hacker an invite

					modified_list = sorted(modified_list)

					remove_emails = set(contacts_list).difference(modified_list) #get the ones no longer in modified_list

					for his_email in remove_emails: #and remove them from the other guy
						try:
							his_account = MONGO_ACCOUNTS.find_one({"email":his_email}) #if not found will raise typeerror
							his_id = his_account["_id"]
							his_contacts = his_account["contacts_list"]
							his_contacts.remove(MY_EMAIL) #for any unknown reason the email is missing, just skip
						except (TypeError, ValueError):
							pass
						else:
							result = MONGO_ACCOUNTS.update_one({"_id":his_id}, {"$set":{"contacts_list" : modified_list}}) #remove him from your own lost
					
					contacts_list=modified_list
					result = MONGO_ACCOUNTS.update_one({"_id":MY_ID}, {"$set":{"contacts_list" : modified_list}}) #upsert True will update (with arg2 )if filter (arg1) not found
				
				success = True
			
			except AssertionError as e:
				success= False
				reason = e[0]
			
			response.update(dict(
				answer="Contacts!",
				data = {
					"success":success,
					"data":contacts_list,
					"reason":reason
				}
			))
		
		if question == "Star?":
						
			#success = bool(MONGO_CLIPS.find_one_and_update({"_id":data["_id"]},{"bookmarked":True}) )
			
			exists = bool(MONGO_CLIPS.find_one({
				"hash":data["hash"],"system":"starred", #it may be multiple hashes exists across different users
				"owner_id":MY_ID, #so enforce with user_id
			})) #find_one returns None if none found
			if not exists:
				success = bool(addClipAndDeleteOld(data, "starred", MY_ID))
			else:
				reason = "already starred"
				success = False

			response.update(dict(
				answer="Star!",
				data = {
					"reason" : reason,
					"success" : success
				}
			))

		if question == "Delete?":
			
			remove_id = data["remove_id"]
			remove_row = data["remove_row"]
			list_widget_name = data["list_widget_name"]
					
			location = list_widget_name, remove_row

			result  = MONGO_CLIPS.delete_one({
				"_id":remove_id, #WARNING comes from user!
				"owner_id":MY_ID, #Mongo ids are not secure alone, make sure the clip belongs to this user before deleting. MY_ID is not spoofable since it cannot not come from the attacker. http://stackoverflow.com/questions/11577450/are-mongodb-ids-guessable
			}).deleted_count
			
			success=bool(result)
			
			print "ROW ID: %s, DELETED: %s"%(remove_id,result)
			
			response.update(dict(
				answer="Delete!",
				data = {
					"success":success,
					"location":location,
					"reason":reason
				}
			))
						
		if question == "Upload?":
				
			container_name =  data or ""
			
			PRINT("container_name", container_name)
			
			file_path = os.path.join(UPLOAD_DIR,container_name)
			
			container_exists = os.path.isfile(file_path)
			
			response.update(dict(
				answer = "Upload!",
				data = container_exists
			))
			
			PRINT("container_exists", container_exists)

		if question == "Update?":
				
			data["owner_id"]=MY_ID
			data['timestamp_server'] = time.time()
			
			prev = (list(MONGO_CLIPS.find({
				#"starred":{"$ne":True},
				"system":"main",
				"owner_id":MY_ID,
			}).sort('_id',pymongo.DESCENDING).limit( 1 ) ) or [{}]).pop() #do not consider starred clips or friends #cannot bool iterators, so must convert to list, and then pop the row
			
			if prev.get("hash") != data.get("hash"):
			
				success = bool(addClipAndDeleteOld(data, "main", MY_ID))
			else:
				
				success = False #DO NOT SEND NONE as this NONE indicates bad connection to client (remember AsyncResult.wait() ) and will result in infinite loop

			response.update(dict(
				answer = "Update!",
				data = {
					"reason":reason,
					"success":success
				}
			))
			
			#PRINT("update", new_clip_id)
			
			#prev = hash
		
		OUTGOING_QUEUE.append(response)
			
		PRINT("incomming", "wait...")
		sleep(0.1)

	wsock.close() #OR IT WILL LEAVE THE GREENLET HANGING!
	
def outgoingGreenlet(wsock, timeout, checkLogin, OUTGOING_QUEUE):
	
	login_result = checkLogin()
	
	MY_ID = login_result["found"]["_id"] #no point in getting from incomming greenlet since it'll close the connection if password changes. WARNING- connection will stay active if user happens to change password
	
	OUTGOING_QUEUE.append(dict(
		answer = "Connected!",
		data = login_result["reason"],
	))
	
	for second in timeout:
	
		sleep(0.1)
	
		try:
				
			send = OUTGOING_QUEUE.pop() #get all the queues first... raises index error when empty.
			
		except IndexError: #then monitor for external changes	
		
			try:	
				if server_latest_clips:
					server_latest_row = server_latest_clips[0]
			
				if server_latest_row.get('_id') != server_previous_row.get('_id'): #change to Reload if signature of last 50 clips changed
					PRINT("sending new",server_latest_row.get('_id'))
					wsock.send(json.dumps(dict(
						answer = "Newest!", #when there is a new clip from an outside source, or deletion
						data = server_latest_clips,
					)))
					server_previous_row = server_latest_row #reset prev
					
				server_latest_clips = [each for each in MONGO_CLIPS.find({
					"_id":{"$gt":server_latest_row["_id"]},
					"owner_id":MY_ID,
				}).sort('_id',pymongo.DESCENDING).limit( 1 )] #DO NOT USE ASCENDING, USE DESCENDING AND THEN REVERSED THE LIST INSTEAD!... AS AFTER 50, THE LATEST CLIP ON DB WILL ALWAYS BE HIGHER THAN THE LATEST CLIP OF THE INITIAL 50 CLIPS SENT TO CLIENT. THIS WILL RESULT IN THE SENDING OF NEW CLIPS IN BATCHES OF 50 UNTIL THE LATEST CLIP MATCHES THAT ON DB.
			
			except UnboundLocalError: #no server previous row
				server_previous_row = {}
				server_latest_clips = [each for each in MONGO_CLIPS.find({"owner_id":MY_ID,}).sort('_id',pymongo.DESCENDING)]#.limit( 5 )] #returns an iterator but we want a list	
			
		else:
			print send
			wsock.send(json.dumps(send))
			
	wsock.close()

@app.route('/ws')
def handle_websocket():
	
	gevent.sleep(1) #prevent many connections
	
	#websocket_id = uuid.uuid4()

	try:		
	
		wsock = request.environ.get('wsgi.websocket')
				
		if not wsock:
			abort(400, 'Expected WebSocket request.')


		def checkLogin(email=request.query.email, password = request.query.password):
		
			###Uncomment to enable Login
			result = login(email, password)
			if not result['success']:
				wsock.send(json.dumps(dict(
					answer = "Error!",
					data = result["reason"],
				)))
				wsock.close()
				raise WebSocketError
			return result
	
		timeout=xrange(40000)
				
		OUTGOING_QUEUE = deque()
		
		args = [wsock, timeout, checkLogin, OUTGOING_QUEUE] #Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.

		#send_update_command.set(None)
				
		greenlets = [
			gevent.spawn(incommingGreenlet, *args),
			gevent.spawn(outgoingGreenlet, *args),
		]
		gevent.joinall(greenlets)

	except WebSocketError:
		abort(500, 'Websocket failure.')
	finally:
		wsock.close()
		
@app.get('/file_exists/<filename>')
def file_exists(filename):
	response.content_type =  "application/json; charset=UTF8"

	file_path = os.path.join(UPLOAD_DIR,filename)
	file_exists = os.path.isfile(file_path)
	
	PRINT("file exists", file_exists)
	
	return json.dumps({"result":file_exists})
		
@app.post('/upload')
def handle_upload():
	#print "HANDLE HANDLE HANDLE"
	result = "OK"
	save_path = UPLOAD_DIR

	upload    = request.files.get('upload')
	
	#name, ext = os.path.splitext(upload.filename)
	"""
	if ext not in (".txt",'.bmp','.png','.jpg','.jpeg', '.py'):
		result = 'File extension not allowed.'
	else:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	"""
	try:
		upload.save(save_path, overwrite=False) # appends upload.filename automatically
	except IOError:
		pass
		
	response.content_type =  "application/json; charset=UTF8"
	return json.dumps({"upload_result":result})

@app.get('/static/<filename>')
def handle_download(filename):
	return static_file(filename, root=UPLOAD_DIR)
	
"""
@app.get('/auth/<email>/<password>')
def register(email,password):
	response.content_type =  "application/json; charset=UTF8"

	found = accounts.find_one({'email': email})

	if not validators.email(email):
		return json.dumps({"success": False, "reason":"Invalid email!"})
	if found:
		return json.dumps({"success": False, "reason":"Email already exists!"})
	if len(password) < 8:
		return json.dumps({"success": False, "reason":"Password too short!"})

	random_bytes = Crypto.Random.get_random_bytes(16).encode("base64")
	key_derivation = PBKDF2(password, random_bytes).encode("base64")
	new_account_id = accounts.insert_one({"email":email, "key_derivation":key_derivation, "salt":random_bytes})
	return {"success":True, "Reason":"Account %s successfully created!"%new_account_id}
"""
if __name__ == "__main__":
	#geventwebsocket implementation
	from gevent.pywsgi import WSGIServer
	from geventwebsocket import WebSocketError
	from geventwebsocket.handler import WebSocketHandler
	server = WSGIServer(("0.0.0.0", 8084), app,
						handler_class=WebSocketHandler)
	server.serve_forever()

"""
##ws4py implementation (doesn't work)
#from gevent import monkey; monkey.patch_all()
from ws4py.server.geventserver import WSGIServer
from ws4py.server.geventserver import WebSocketWSGIHandler
from ws4py.exc import WebSocketException

server = WSGIServer(("0.0.0.0", 8084), app,
					handler_class=WebSocketHandler )
server.serve_forever()
"""
