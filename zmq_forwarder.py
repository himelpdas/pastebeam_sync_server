__author__ = 'Himel'
from gevent import monkey; monkey.patch_all()
from functions import LOG
import zmq.green as zmq  #http://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/devices/forwarder.html



def main():
    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.SUB)
        frontend.bind("tcp://*:8882")

        frontend.setsockopt(zmq.SUBSCRIBE,
                            "")  #"" means subscribe to the socket, and don't filter anything (since this is a forwarder and we want all messages to pass # Another important thing to notice is that we want all the published messages to reach to the various subscribers, hence message filtering should be off in the forwarder device. See line no 11.

        # Socket facing services
        backend = context.socket(zmq.PUB) #as of zmq 3, message filtering is done here... in other words, zmq will only send it to the websocket subscriber listening for himeldas@live.com... Before it was the responsibility of the subscriber to filter, so the filtering would've been done in the websocket server, instead of here. This can get very bad for the websocket, if there are lots of messages
        backend.bind("tcp://*:8883")

        zmq.device(zmq.FORWARDER, frontend, backend)
    except Exception, e:
        print e
        LOG.error(e)
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()


if __name__ == "__main__":
    main()
