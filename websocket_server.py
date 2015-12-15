# TODO get sentry to track stacktraces
from gevent import monkey; monkey.patch_all()  # declare BEFORE all imports

import wsaccel  # speeds up geventwebsocket https://bitbucket.org/noppo/gevent-websocket

from classic_server import *
import zmq.green as zmq
from collections import deque
import uuid, time


def PRINT(label, data):
    print "\n%s: %s" % (label.capitalize(), data)


@app.route('/echo')
def test_async_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')

    while True:
        try:
            message = wsock.receive()
            # sleep(8)
            wsock.send(message)
        except WebSocketError:
            break


def add_clip_and_delete_old(data, system, owner_id, publisher, broadcast_email):
    data["owner_id"] = owner_id
    data["system"] = system
    data['timestamp_server'] = time.time()

    redundant = MONGO_CLIPS.find({'hash':data["hash"], 'system':system})

    for each_redundant in redundant:
        delete_single_clip(each_redundant["_id"], owner_id, broadcast_email, publisher, delete_container=False)  # user did not expl. say so
    #gevent.sleep(.1)  # can be sent after newest, resulting in new clip in client before old clip delete

    _id = bool(MONGO_CLIPS.insert_one(data).inserted_id)

    # find old crap
    tmp_free_user_limit = 5
    old = MONGO_CLIPS.find({
        "system": system,
        "owner_id": owner_id,
    }).sort('_id', pymongo.DESCENDING)[tmp_free_user_limit:]

    old_list = list(old)  # mongo results are iterators, so turn into list if using more than once

    # delete old crap
    MONGO_CLIPS.delete_many({"_id": {'$in': map(lambda each: each["_id"], old_list)}})
    for each_old_clip in old_list:
        delete_single_clip(each_old_clip["_id"], owner_id, broadcast_email, publisher)

    #publish change
    publisher.send_string(u"%s newest %s" % (broadcast_email, json.dumps([data]))) #data needs to be in list

    return _id


def delete_clip_file_and_versions(clip_to_delete):

    if clip_to_delete:
        if not clip_to_delete["system"] == "notification":
            container_name = clip_to_delete["container_name"]
            all_file_versions = GRID_FS.find({"filename":container_name})
            for each_file in all_file_versions:
                GRID_FS.delete(each_file._id)
            success = True
        else:
            LOG.info("Notifications don't have files: %s" % clip_to_delete["_id"])
            success = False
    else:
        LOG.info("delete_clip_file_and_versions: File already deleted: %s" % clip_to_delete["_id"])
        success = False
    return success

def delete_single_clip(remove_id, owner_id, owner_email, publisher, delete_container=True):

    delete_location = str(remove_id)

    clip_to_delete = MONGO_CLIPS.find_one({"_id":remove_id, "owner_id":owner_id})

    if delete_container and clip_to_delete:
        delete_clip_file_and_versions(clip_to_delete)

    result = MONGO_CLIPS.delete_one({
        "_id": remove_id,  # WARNING comes from user!
        "owner_id": owner_id,
        # Mongo ids are not secure alone, make sure the clip belongs to this user before deleting. MY_ID is not spoofable since it cannot not come from the attacker. http://stackoverflow.com/questions/11577450/are-mongodb-ids-guessable
    }).deleted_count

    data = {"location": delete_location}

    publisher.send_string(u"%s delete %s" % (owner_email, json.dumps(data)))

    success = bool(result)

    return success


def add_notification(for_account, reason, publisher, from_email=None, notification_type=u"confirmation"):
    for_id = for_account["_id"]
    my_email = for_account["email"]
    if not from_email:
        from_email = my_email
    data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(), u'clip_type': notification_type,
            "session_id": str(uuid.uuid4()), "hash": str(uuid.uuid4()),
            u'host_name': from_email}  # uuid as a dummy hash is needed so it is not ignored by client or server
    add_clip_and_delete_old(data, "notification", for_id, publisher, my_email)


def incoming_greenlet(wsock, timeout, MY_ACCOUNT, checkLogin, publisher,
                      OUTGOING_QUEUE):  # these seem to run in another namespace, you must pass them global or inner variables
    # """Checks login every incoming request"""
    for second in timeout:  # Even though greenlets don't use much memory, if the user disconnects, this server greenlet will run forever, and this "little memory" will become a big problem

        LOG.info("incoming_greenlet: wait...")

        received = wsock.receive()

        if not received:
            raise WebSocketError

        delivered = json.loads(received)

        question = delivered['question']

        data = delivered['data']

        LOG.info("incoming_greenlet: delivered: %s" % data)

        response = {"echo": delivered["echo"]}

        success = reason = None

        # TODO- move this back to handle_websocket, and disconnect all websockets via web2py and 0mq when user account changes
        MY_ACCOUNT.update(checkLogin()["found"])
        MY_ID = MY_ACCOUNT[
            "_id"]  # need to keep this the most updated, incoming greenlet is ideal since it blocks and will reduce db hits
        MY_EMAIL = MY_ACCOUNT["email"].lower()
        MY_FIRST_NAME, MY_LAST_NAME = MY_ACCOUNT["first_name"].capitalize(), MY_ACCOUNT["last_name"].capitalize()
        MY_FULL_NAME = "%s %s"%(MY_FIRST_NAME, MY_LAST_NAME)

        if question == "Share?":
            his_email = data["recipient"]
            his_account = MONGO_ACCOUNTS.find_one({"email": his_email})
            his_id = his_account["_id"]
            his_name = "%s %s" % (his_account["first_name"].capitalize(), his_account["last_name"].capitalize())
            try:
                assert MY_EMAIL in his_account["contacts_list"], "You are not in this user's contacts!"

                his_clips = MONGO_CLIPS.find({"owner_id": his_id})
                assert not data["hash"] in map(lambda each_clip: each_clip["hash"],
                                               his_clips), "%s already has an item you just sent!" % his_name

                # final modifications before sending to recipient's clips
                data["host_name"] = MY_EMAIL
                data.pop("_id", None)  # or else duplicate error

                success = add_clip_and_delete_old(data, "share", his_id, publisher, his_email)
            except AssertionError as e:
                my_reason = e[0]
            else:
                his_reason = "%s sent you an item" % MY_FULL_NAME
                add_notification(his_account, his_reason, publisher, MY_EMAIL)
                
                my_reason = "You sent a clip to %s" % his_name

            add_notification(MY_ACCOUNT, my_reason, publisher, his_email)

            response.update(dict(
                answer="Share!",
                data={
                    "success": success,
                    "reason": my_reason
                }
            ))

        if question == "Publickey?":
            try:
                his_email = data
                his_account = MONGO_ACCOUNTS.find_one({"email": his_email})
                assert MY_EMAIL in his_account["contacts_list"], "You are not in this user's contacts! (Error 107)"
                his_public_key = his_account["rsa_public_key"]
            except AssertionError as e:
                reason = e[0]
                his_public_key = None
            response.update(dict(
                answer="Publickey!",
                data={
                    "success": his_public_key,
                    "reason": reason
                }
            ))

        if question == "Invite?":

            his_email = data["email"].lower()

            previous_invite = MONGO_INVITES.find_one({"owner_id": MY_ID, "to": his_email})

            try:

                assert MY_EMAIL != his_email, "Cannot send an invite to yourself! (Error 88)"

                if previous_invite:
                    now = datetime.datetime.utcnow()
                    delta = now - previous_invite["date"]
                    days = delta.days

                    assert days >= 2, "You can send an invite to this person once every 48 hours! (Error 95)"
                    # delete old friend request
                    MONGO_INVITES.delete_one({"_id": previous_invite["_id"],
                                              "owner_id": MY_ID})  # owner_id not needed as this _id is not known by attacker, however it may be needed for indexing

                MONGO_INVITES.insert_one({"owner_id": MY_ID, "to": his_email, "used": False,
                                          "date": datetime.datetime.utcnow()})  # TODO- add a clip when non-registered user joins

                his_account = MONGO_ACCOUNTS.find_one({"email": his_email})
                if his_account:

                    assert not ((MY_EMAIL in his_account["contacts_list"]) and (his_email in MY_ACCOUNT[
                        "contacts_list"])), "You both are already in each other's contacts! (Error 145)"  # basically a NAND gate. Allow if one or both are in each other's contacts (maybe one deleted by mistake?)

                    his_first_name, his_last_name = his_account["first_name"].capitalize(), his_account[
                        "last_name"].capitalize()

                    reason = "{first_name} {last_name} sent you a contact invite!".format(first_name=MY_FIRST_NAME,
                                                                                          last_name=MY_LAST_NAME)
                    add_notification(his_account, reason, publisher, MY_EMAIL, notification_type=u"invite")

                    reason = "You sent {first_name} {last_name} a contact invite!".format(first_name=his_first_name,
                                                                                          last_name=his_last_name)
                    add_notification(MY_ACCOUNT, reason, publisher, his_email)
                else:
                    pass  # EMAIL THIS PERSON TO JOIN

                success = True

            except AssertionError as e:
                success = False
                reason = e[0]

            response.update(dict(
                answer="Invite!",
                data={
                    "success": success,
                    "reason": reason
                }
            ))

        if question == "Accept?":

            his_email = data["email"].lower()

            his_account = MONGO_ACCOUNTS.find_one({"email": his_email})

            try:
                assert his_email, "Malformed request. (Error 126)"
                assert his_account, "Invite sender not found. Maybe acccount was deleted? (Error 127)"

                his_id = his_account["_id"]

                assert his_email != MY_EMAIL, "You cannot accept your own email. (Error 132)"

                # see if the email this user wants to add is in a corresponding invite
                previous_invite = MONGO_INVITES.find_one({"owner_id": his_id, "to": MY_EMAIL})

                assert previous_invite, "No invitation found from this user! (Error 152)"

                assert not previous_invite[
                    "used"], "Invitation had been already used. Try sending a new invite. (Error 155)"

                def _addEmailToContacts(account, add_email):
                    _id = account["_id"]
                    contacts = list(set(account["contacts_list"] + [add_email]))
                    MONGO_ACCOUNTS.update_one({"_id": _id}, {"$set": {
                        "contacts_list": contacts}})  # upsert True will update (with arg2 )if filter (arg1) not found

                    publisher.send_string(u"%s contacts %s" % (add_email, json.dumps(contacts)))

                _addEmailToContacts(MY_ACCOUNT, his_email)
                _addEmailToContacts(his_account, MY_EMAIL)

                reason = "{first_name} {last_name} accepted your contact invite!".format(
                    first_name=his_account["first_name"].capitalize(), last_name=his_account["last_name"].capitalize())
                data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(),
                        u'clip_type': u'confirmation', "session_id": None, "hash": str(uuid.uuid4()),
                        u'host_name': MY_EMAIL}  # uuid as a dummy hash

                add_clip_and_delete_old(data, "notification", his_id, publisher, his_email)

                reason = "You accepted a contact invite from {first_name} {last_name}!".format(
                    first_name=his_account["first_name"].capitalize(), last_name=his_account["last_name"].capitalize())
                data = {u'clip_display': reason, u'timestamp_server': datetime.datetime.utcnow(),
                        u'clip_type': u'confirmation', "session_id": None, "hash": str(uuid.uuid4()),
                        u'host_name': his_email}  # uuid as a dummy hash

                add_clip_and_delete_old(data, "notification", MY_ID, publisher, MY_EMAIL)

                MONGO_INVITES.find_one_and_update({"_id": previous_invite["_id"]}, {"$set": {"used": True}})

                success = True

            except AssertionError as e:
                success = False
                reason = e[0]

            response.update(dict(
                answer="Accept!",
                data={
                    "success": success,
                    "reason": reason
                }
            ))

        if question == "Contacts?":
            # IN PROGRESS

            try:
                modified_list = data[
                    "contacts_list"]  # Modified list will ALWAYS be less than or equal to contacts, since the only way to add contacts is via invites

                contacts_list = sorted(MY_ACCOUNT["contacts_list"])

                if modified_list != None:  # [] is valid, None is just get

                    assert all(validators.email(each_email) for each_email in
                               modified_list), "An email failed validation. (Error 206)"  # this is a setter, so make sure it passes validation

                    assert set(modified_list).issubset(
                        contacts_list), "Illegal operation. (Error 209)"  # make sure user's modified_list does not have anything that's not in original contacts list. IE hacker may want to add someone else's email who did not send hacker an invite

                    modified_list = sorted(modified_list)

                    remove_emails = set(contacts_list).difference(
                        modified_list)  # get the ones no longer in modified_list

                    for his_email in remove_emails:  # and remove them from the other guy
                        try:
                            his_account = MONGO_ACCOUNTS.find_one(
                                {"email": his_email})  # if not found will raise typeerror
                            his_id = his_account["_id"]
                            his_contacts = his_account["contacts_list"]
                            his_contacts.remove(MY_EMAIL)  # for any unknown reason the email is missing, just skip
                        except (TypeError, ValueError):
                            pass
                        else:
                            result = MONGO_ACCOUNTS.update_one({"_id": his_id}, {
                                "$set": {"contacts_list": his_contacts}})  # remove him from your own lost
                            publisher.send_string(u"%s contacts %s" % (his_email, json.dumps(his_contacts)))

                    contacts_list = modified_list
                    result = MONGO_ACCOUNTS.update_one({"_id": MY_ID}, {"$set": {
                        "contacts_list": modified_list}})  # upsert True will update (with arg2 )if filter (arg1) not found
                    publisher.send_string(u"%s contacts %s" % (MY_EMAIL, json.dumps(contacts_list)))
                success = True

            except AssertionError as e:
                success = False
                reason = e[0]

            # gevent.sleep(30) #test dialog

            response.update(dict(
                answer="Contacts!",
                data={
                    "success": success,
                    "contacts": contacts_list,
                    "reason": reason
                }
            ))

        if question == "Star?":
            # success = bool(MONGO_CLIPS.find_one_and_update({"_id":data["_id"]},{"bookmarked":True}) )

            exists = bool(MONGO_CLIPS.find_one({
                "hash": data["hash"], "system": "starred",  # it may be multiple hashes exists across different users
                "owner_id": MY_ID,  # so enforce with user_id
            }))  # find_one returns None if none found
            if not exists:
                if "_id" in data:
                    del data["_id"] #this will have an ID, but mongo can't insert if _id is present
                success = bool(add_clip_and_delete_old(data, "starred", MY_ID, publisher, MY_EMAIL))
            else:
                reason = "Already starred"
                success = False

            response.update(dict(
                answer="Star!",
                data={
                    "reason": reason,
                    "success": success
                }
            ))

        if question == "Delete?":

            remove_id = data["remove_id"]

            success = delete_single_clip(remove_id, MY_ID, MY_EMAIL, publisher)

            if not success:
                reason = "Already deleted on server"

            data = {
                    "success": success,
                    "reason": reason
                }

            response.update(dict(
                answer="Delete!",
                data=data,
            ))

        if question == "Upload?":
            container_name = data or ""

            LOG.info("container_name: %s" % container_name)

            file_path = os.path.join(UPLOAD_DIR, container_name)

            container_exists = os.path.isfile(file_path)

            response.update(dict(
                answer="Upload!",
                data={
                    "container_exists": container_exists,
                    "success": True,
                    "reason": reason,
                }
            ))

            LOG.info("incoming_greenlet: container_exists: %s" % container_exists)

        if question == "Update?":

            data["owner_id"] = MY_ID
            data['timestamp_server'] = time.time()

            prev = (list(MONGO_CLIPS.find({
                # "starred":{"$ne":True},
                "system": "main",
                "owner_id": MY_ID,
            }).sort('_id', pymongo.DESCENDING).limit(1)) or [{}]).pop()  # do not consider starred clips or friends #cannot bool iterators, so must convert to list, and then pop the row

            if prev.get("hash") != data["hash"]:
                success = bool(add_clip_and_delete_old(data, "main", MY_ID, publisher, MY_EMAIL))
            else:

                success = False  # DO NOT SEND NONE as this NONE indicates bad connection to client (remember AsyncResult.wait() ) and will result in infinite loop
                reason = "Already synced"
            response.update(dict(
                answer="Update!",
                data={
                    "reason": reason,
                    "success": success
                }
            ))

            # PRINT("update", new_clip_id)

            # prev = hash

        OUTGOING_QUEUE.append(response)

        #sleep(.01)  # not needed because receive is blocking (before monkey-patch) and therefore yields

    wsock.close()  # OR IT WILL LEAVE THE GREENLET HANGING!


def outgoingGreenlet(wsock, timeout, MY_ACCOUNT, checkLogin, publisher, OUTGOING_QUEUE):
    # """does not check login every iteration, so in the case of changed password, an attacker can get updates until websocket expires"""
    MY_ID = MY_ACCOUNT["_id"]  # no point in getting from incoming greenlet since it'll close the connection if password changes. WARNING- connection will stay active if user happens to change password

    OUTGOING_QUEUE.append(dict(
        answer="@connected",
        data={
            "initial_contacts": MY_ACCOUNT["contacts_list"],
            "rsa_private_key": MY_ACCOUNT["rsa_private_key"],
            "rsa_pbkdf2_salt": MY_ACCOUNT["rsa_pbkdf2_salt"]
        },
    ))

    server_latest_clips = [each for each in MONGO_CLIPS.find({
        #"_id": {"$gt": server_latest_row["_id"]},
        "owner_id": MY_ID,
    }).sort('_id', pymongo.DESCENDING).limit(
        5*4)]  # DO NOT USE ASCENDING, USE DESCENDING AND THEN REVERSED THE LIST INSTEAD!... AS AFTER 50, THE LATEST CLIP ON DB WILL ALWAYS BE HIGHER THAN THE LATEST CLIP OF THE INITIAL 50 CLIPS SENT TO CLIENT. THIS WILL RESULT IN THE SENDING OF NEW CLIPS IN BATCHES OF 50 UNTIL THE LATEST CLIP MATCHES THAT ON DB.


    OUTGOING_QUEUE.append(dict(
        answer="@newest_clips",
        data=server_latest_clips,
    ))

    prev = set([])

    for second in timeout:

        sleep(.01)

        try:

            send = OUTGOING_QUEUE.pop()  # get all the queues first... raises index error when empty.

        except IndexError:  # then monitor for external changes

            pass

        else:
            LOG.info("outgoingGreenlet: %s" % send)
            if "@newest_clips" in send["answer"]:
                # prevents looped updating
                hashes = set([])
                for each in send["data"]:
                    hashes.add(each["_id"])
                if hashes == prev:  # don't double send
                    continue
                else:
                    prev = hashes

            wsock.send(json.dumps(send))
            LOG.info("outgoingGreenlet: wait...")

    wsock.close()


def subscriberGreenlet(wsock, timeout, MY_ACCOUNT, OUTGOING_QUEUE, port=8883):
    # Socket to talk to server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:%s" % port)
    topicfilter = MY_ACCOUNT["email"]
    socket.setsockopt_string(zmq.SUBSCRIBE, topicfilter)
    # listener
    for second in timeout:
        LOG.info("subscriberGreenlet: wait...")
        string = socket.recv_string()
        LOG.info("subscriberGreenlet: %s" % string)
        action = string.split(" ")[1]
        if action == "kill":
            wsock.close()
        payload = " ".join(string.split(" ")[2:])
        data = json.loads(payload)
        if action == "delete":
            answer = {
                "answer": "@delete_local",
                "data": data,
            }
        elif action == "contacts":
            answer = {
                "answer": "@get_contacts",
                "data": data,
            }
        elif action == "newest":
            answer = {
                "answer": "@newest_clips",
                "data": data,
            }
        OUTGOING_QUEUE.append(answer)
        #gevent.sleep(0.01)


@app.route('/ws')
def handle_websocket():
    gevent.sleep(1)  # prevent many connections

    # websocket_id = uuid.uuid4()

    wsock = request.environ.get('wsgi.websocket')

    if not wsock:
        abort(400, 'Expected WebSocket request.')

    def checkLogin(email=request.query.email, password=request.query.password):

        ###Uncomment to enable Login
        result = login(email, password)
        if not result['success']:
            wsock.send(json.dumps(dict(
                answer="@error",
                data=result["reason"],
            )))
            wsock.close()
            abort(500, 'Invalid account.')
        return result

    def handle_exception(greenlet=None):
        try:
            LOG.error(type(greenlet.exception))
        except Exception, e:
            LOG.error(e)  # THIS HAPPENS WHEN THERE IS NO MONGO CONNECTION
        finally:
            #wsock.shutdown()  # socket still lingers after close (hence the 1024 socket limit error over time), this seems to solve that # http://stackoverflow.com/questions/409783/socket-shutdown-vs-socket-close
            wsock.close()
            abort(500, 'Websocket failure.')

    timeout = xrange(40000)

    OUTGOING_QUEUE = deque()

    try:
        MY_ACCOUNT = checkLogin()["found"]
    except pymongo.errors.ServerSelectionTimeoutError:
        handle_exception()

    def setup_pub(port=8882):
        publisher_context = zmq.Context()
        publisher_socket = publisher_context.socket(zmq.PUB)
        publisher_socket.connect("tcp://localhost:%s" % port)
        return publisher_socket

    args = [wsock, timeout, MY_ACCOUNT, checkLogin, setup_pub(),
            OUTGOING_QUEUE]  # Only objects in the main thread are visible to greenlets, all other cases, pass the objects as arguments to greenlet.

    # send_update_command.set(None)
    g1 = gevent.spawn(incoming_greenlet, *args)
    g1.link_exception(handle_exception)
    g2 = gevent.spawn(outgoingGreenlet, *args)
    g2.link_exception(handle_exception)
    g3 = gevent.spawn(subscriberGreenlet, wsock, timeout, MY_ACCOUNT, OUTGOING_QUEUE)
    g3.link_exception(handle_exception)
    greenlets = [g1,g2,g3]
    gevent.joinall(greenlets)


if __name__ == "__main__":
    # geventwebsocket implementation
    # USE GUNICORN WORKER IN PRODUCTION https://pypi.python.org/pypi/gevent-websocket/
    from gevent.pywsgi import WSGIServer
    from geventwebsocket import WebSocketError
    from geventwebsocket.handler import WebSocketHandler

    server = WSGIServer(("0.0.0.0", 8084), app,  # app must be a WSGI application object, as defined by PEP 333. (Basically a callable that can take the environmental variables, and the response socket iterable)
                        handler_class=WebSocketHandler)  # handler_class basically allows to modify the environmental variables, perhaps making the request compatible with websockets
    server.serve_forever()
