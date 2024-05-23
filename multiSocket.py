import socket
from threading import Thread
import multiprocessing as mp
import json
from _thread import start_new_thread
import netifaces

selfIpAddrs = []
for interface in netifaces.interfaces():
    if 2 in list(netifaces.ifaddresses(interface).keys()):
        selfIpAddrs.append(netifaces.ifaddresses(interface)[2][0]['addr'])

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
        """ Creates a socket in a separate process
        
        Args:
            host (str): IP address to bind to
            port (int): Port to bind to
            socketType (str): "TCP" or "UDP"
            **logMsgs (bool): log incoming messages in console
            **msgCb (function): callback for incoming messages
            **connectStatusCb (function): callback for connection status changes
        """
        
        self.host = host
        self.port = port
        self.socketTypeObj = retSocketType(socketType)
        self.socketTypeStr = socketType
        self.pipeMain, self.pipeChild = mp.Pipe(True)
        self.logMsgs = kwargs.get("logMsgs")
        self.msgCb = kwargs.get("msgCb")
        self.statCb = kwargs.get("connectStatusCb")
        
        if(self.msgCb):
            self.mainProcPipe, self.toMainProc = mp.Pipe(False)

        self.createProc()
        
        if(self.msgCb):
            self.passMsgs = Thread(target=self.passMsgsFn)
            self.passMsgs.start() 
        
    def passMsgsFn(self):
        """
            Passes messages from child process back to the original process, where the message callback is.
        """
        while True:
            msg = self.mainProcPipe.recv()
            # print("64", msg)
            self.msgCb(msg['msg'], addr=msg['addr'][0], port=msg['addr'][1])

    def createProc(self):
        proc = mp.Process(target=self.createSocket, args=())
        proc.start()

    def createSocket(self):
        self.sock = socket.socket(socket.AF_INET, self.socketTypeObj)
        if(self.socketTypeStr == "UDP"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.sock.bind((self.host, self.port))
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
        """
            Reads incoming UDP packets, sends to original process if callback specified.
        """
        while True:
            data, address = self.sock.recvfrom(1024)
            if address[0] not in selfIpAddrs: # Sent messages show up as received sometimes, exclude that
                if self.msgCb:
                    passThrough = {}
                    passThrough["msg"] = data.decode()
                    passThrough["addr"] = address
                    self.toMainProc.send(passThrough)
                else:
                    print("CB ERR:",passThrough)

    def readOutgoing(self):
        """
            Reads messages from the main process and sends them out.
        """
        while True:
            data = self.pipeChild.recv()
            # print("121: ",data)
            jsonMsg = json.loads(data)
            jsonKeys = list(jsonMsg.keys())
            if self.logMsgs:
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
                    try:
                        TCPIPMap[ip].sendall(msg)
                    except Exception as e:
                        print("115",e)
                        print(ip)
                        if self.statCb:
                            self.statCb("DISCONNECTED", ip)
                else:
                    print("NO ROLE OR CONNECTION TO: ",ip)
            else: 
                self.sock.sendto(msg.encode(), (ip, port))

    def send(self, msg, address, **kwargs):
        """
            Sends a message to the specified address.

        Args:
            msg (str): message to send
            address (str): ip address to send to
            **sendToPort (int): port to send to, defaults to the port the socket was created on
        """
        # print("152 ", msg, address)
        port = kwargs.get("sendToPort")
        if port == None:
            port = self.port
        
        self.pipeMain.send(json.dumps({"msg":msg, "IP":address, "PORT":port}))
        
    def tcpConnHandler(self):
        """
            Handles incoming TCP connections by creating a new thread for each connection.
        """
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
            try:
                data = conn.recv(1048)
            except:
                if self.statCb:
                    self.statCb("DISCONNECTED", addr[0])
                break
            passThrough = {}
            passThrough["msg"] = data.decode()
            passThrough["addr"] = addr
            self.toMainProc.send(passThrough)
            if not data:
                if self.statCb:
                    self.statCb("DISCONNECTED", addr[0])
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
