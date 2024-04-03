import socket
from threading import Thread
import multiprocessing as mp
import json
from _thread import start_new_thread

global TCPIPMap # {ip:tcpObject}
TCPIPMap = {}

def retSocketType(socketType):
    if socketType == "TCP":
        return socket.SOCK_STREAM
    elif socketType == "UDP":
        return socket.SOCK_DGRAM
    else:
        return None

def addHeader(msg):
    """
        Adds \r\n and message length to beginning of packets.
        Also converts to utf-8
    """
    try:
        msg = json.dumps(msg)
        msgLength = len(msg.encode('utf-8'))
        numAddBytes = 8-msgLength
        addBytes = "0"*numAddBytes
        hdr = "\r\n" + addBytes
        foot = b'\xFF'
        bz = bytearray((hdr + msg).encode('utf-8')) + foot
        return bz
    except Exception as e:
        print("ADDHEADER: ",e)

class MultiSocket:
    def __init__(self, host, port, socketType, **kwargs):
        self.host = host
        self.port = port
        self.socketTypeObj = retSocketType(socketType)
        self.socketTypeStr = socketType
        self.pipeMain, self.pipeChild = mp.Pipe(True)
        self.logMsgs = kwargs.get("logMsgs")
        self.msgCb = kwargs.get("msgCb")
        self.statCb = kwargs.get("connectStatusCb")

        self.createProc()

    def createProc(self):
        proc = mp.Process(target=self.createSocket, args=())
        proc.start()

    def createSocket(self):
        self.sock = socket.socket(socket.AF_INET, self.socketTypeObj)
        if(self.socketTypeStr == "UDP"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.sock.bind((self.host, self.port))
            if self.logMsgs:
                print(self.socketTypeStr + " socket created on: ", self.host, ":", self.port)

            inboundThread = Thread(target=self.readIncomingUDP)
            inboundThread.start()

            outboundThread = Thread(target=self.readOutgoing)
            outboundThread.start()

        elif(self.socketTypeStr == "TCP"):
            global TCPComeUp
            TCPComeUp = False
            while TCPComeUp == False:
                try:
                    self.sock.bind((self.host, self.port))
                    TCPComeUp = True
                    print("TCP Socket bound to ",self.host,self.port)
                except OSError:
                    pass
            self.sock.listen()

            handleConnThread = Thread(target=self.tcpConnHandler)
            handleConnThread.start()

            outboundThread = Thread(target=self.readOutgoing)
            outboundThread.start()


    def readIncomingUDP(self):
        while True:
            data = self.sock.recv(1024)
            if self.msgCb:
                self.msgCb(data)
            else:
                print("CB ERR:",data)

    def readOutgoing(self):
        while True:
            data = self.pipeChild.recv()
            jsonMsg = json.loads(data)
            jsonKeys = list(jsonMsg.keys())
            print("LINE 105: ",jsonMsg)

            msg = jsonMsg["msg"]
            if "IP" in jsonKeys:
                ip = jsonMsg["IP"]
            if "PORT" in jsonKeys:
                port = jsonMsg["PORT"]
            else:
                port = self.port

            if self.socketTypeStr == "TCP":
                msg = addHeader(msg)
                if ip in TCPIPMap:
                    TCPIPMap[ip].sendall(msg)
                else:
                    print("NO ROLE OR CONNECTION TO: ",ip)
            else: 
                self.sock.sendto(msg, (ip, port))

    def send(self, msg, address,**kwargs):
        port = kwargs.get("sendToPort")
        if port == None:
            port = self.port
        
        self.pipeMain.send(json.dumps({"msg":msg, "IP":address, "PORT":port}))
        
    def tcpConnHandler(self):
        while True:
            TCPConnection, address = self.sock.accept()
            # if self.statCb:
                # self.statCb("CONNECTED", addr=address[0])

            start_new_thread(self.onNewTCPConnection, (TCPConnection, address))

    def onNewTCPConnection(self, conn, addr):
        global TCPIPMap
        TCPIPMap[addr[0]] = conn
        self.statCb("CONNECTED", addr[0])
        while True:
            data = conn.recv(1048)
            self.msgCb(data, addr=addr[0])
            if not data:
                if self.statCb:
                    self.statCb("DISCONNECT", addr[0])
                break

            # data = conn.recv(2)
            # if not data:
            #     if self.statCb:
            #         self.statCb("DISCONNECT", addr[0])
            #     break
            # data = data.decode('utf-8')
            # # first two bytes are \r\n to indicate start of packet
            # if "\r\n" in data:
            #     try:
            #         data = conObj.recv(8)
            #         print("182: ",data)
            #         # next 8 bytes are the length of the packet
            #         dLength = int(data)
            #         try:
            #             pkt = conObj.recv(dLength).decode('utf-8')
            #         except Exception as e:
            #             print(e)
            #         self.msgCb(pkt, addr=addr[0])
            #     except:
            #         print("JSON ERROR in MultiSocket 198")
            # if not data: # disconnect
            #     if self.statCb:
            #         self.statCb("DISCONNECT",addr[0])
            #     break
