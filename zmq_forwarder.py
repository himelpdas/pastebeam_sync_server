__author__ = 'Himel'
from gevent import monkey; monkey.patch_all()
import zmq.green as zmq  #http://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/devices/forwarder.html



def main():
    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.SUB)
        frontend.bind("tcp://*:8882")

        frontend.setsockopt(zmq.SUBSCRIBE,
                            "")  # The current version of zmq supports filtering of messages based on topics at subscriber side. This is usually set via socketoption.

        # Socket facing services
        backend = context.socket(zmq.PUB)
        backend.bind("tcp://*:8883")

        zmq.device(zmq.FORWARDER, frontend, backend)
    except Exception, e:
        print e
        print "bringing down zmq device"
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()


if __name__ == "__main__":
    main()
