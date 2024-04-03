from multiSocket import MultiSocket
import time
import queue

global dumbQueue
dumbQueue = queue.Queue()
global connections
connections = {}

def out(data, **args):
    # print(args.get("addr"))
    # print("LINE 4: ",data)
    udpSock.send(data, sendToIp=args.get("addr"))


def conStat(stat, addr):
    if stat == "CONNECTED":
        roleQuery = {}
        roleQuery["ROLE"] = "ROLE"

        queueobj = {}
        queueobj["msg"] = roleQuery
        queueobj["addr"] = addr
        global dumbQueue
        dumbQueue.put(queueobj)
        print(dumbQueue)


if __name__ == '__main__':
    udpSock = MultiSocket("0.0.0.0", 12345, "UDP", logMsgs=True, msgCb=out, connectStatusCb=conStat)
    while True:
        # time.sleep(3)
        # udpSock.send("Hello World", sendToIp="192.168.1.223")

        if not dumbQueue.empty():
            try:
                qmsg = dumbQueue.get()
                print("LINE 27: ",qmsg)
                udpSock.send(qmsg["msg"].encode('utf-8'), sendToIp=qmsg["addr"])
            except:
                pass
       