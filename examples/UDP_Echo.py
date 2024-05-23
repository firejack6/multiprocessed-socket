from multiprocessed_socket import MultiSocket
import time
import queue

global dumbQueue
dumbQueue = queue.Queue()
global connections
connections = {}

def out(data, **kwargs):
    """
        loopback - echoes back to sender

    Args:
        data (str): incoming message
        **addr (str): ip address of sender
        **port (int): port of sender
    """
    Sock.send(data, kwargs.get("addr"), sendToPort=kwargs.get('port'))


def conStat(stat, addr):
    # print("16: ",stat, addr)
    if stat == "CONNECTED":
        roleQuery = {}
        roleQuery["ROLE"] = "ROLE"

        queueobj = {}
        queueobj["msg"] = roleQuery
        queueobj["addr"] = addr
        global dumbQueue
        dumbQueue.put(queueobj)
        # print(dumbQueue)


if __name__ == '__main__':
    Sock = MultiSocket("0.0.0.0", 12345, "UDP", logMsgs=True, msgCb=out, connectStatusCb=conStat)
    while True:
        # time.sleep(3)
        # udpSock.send("Hello World", sendToIp="192.168.1.223")

        if not dumbQueue.empty():
            try:
                qmsg = dumbQueue.get()
                print("LINE 27: ",qmsg)
                Sock.send(qmsg["msg"].encode('utf-8'), sendToIp=qmsg["addr"])
            except:
                pass