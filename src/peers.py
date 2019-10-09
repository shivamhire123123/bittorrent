import tracker
import torrent_file
import sys
import struct
from socket import *
from torrent_logger import *
import threading

def filter_tracker(tracker, protocol):
    ''' This function takes a list of strings contaning url to different trackers
    and return a list of trackers which have the given protocol. It is expected
    that protocol will be one udp or http'''
    filter_trackers = []
    for i in tracker:
        if (i.find(protocol) != -1):
            filter_trackers.append(i)

    return filter_trackers

class peers:
    def __init__(self, ip, port):
        # Upload speed of peer averaged so far
        self.upload_speed = None
        # Download speed
        self.download_speed = None

        # 4 state variable for peers
        self.am_chocking = 1
        self.am_interested = 0
        self.peer_chocking = 1
        self.peer_interested = 0
		# Lock for updating peer state
		self.state_lock = threading.Lock()

        # Use to communicate to peer
        self.ip = ip
        self.connection_port = port
        self.socket = None
        self.socket_lock = threading.Lock()

        # This variable is set by main_peer_thread, receiver_thread or sender_thread
        # to notify other thread to shutdown
        self.quit = 0
        self.quit_lock = threading.Lock()

		# bitfield set having those numbers which the peer have
		self.bitfield = {}
		self.bitfield_lock = threading.Lock()

    def locked_socket_send(self, data):
        with self.socket_lock:
            return self.socket.send(data)

    def locked_socket_recv(self, length):
        response = b''
        with self.socket_lock:
            while len(response) != response:
                response += self.socket.recv(length - len(response))
        return response

    def handshake(self, torrent):
        self.pstr = "BitTorrent protocol"
        self.pstrlen = struct.pack("!B", len(self.pstr))
        self.pstr = struct.pack("!" + str(len(self.pstr)) + "s", self.pstr.encode())
        self.reserved = struct.pack("!Q", 0)
        self.info_hash = b''
        for i in torrent.info_hash.digest():
            self.info_hash += struct.pack("!B", i)
        self.peer_id = b''
        for i in torrent.peer_id:
            self.peer_id += struct.pack("!B", i)

        peers_logger.debug("pstrlen - " + str(self.pstrlen))
        peers_logger.debug("pstr - " + str(self.pstr))
        peers_logger.debug("info_hash - " + str(self.info_hash))
        peers_logger.debug("peer_id - " + str(self.peer_id))
        peers_logger.debug("length of info_hash and peer_id is " + str(len(self.info_hash)) + " and " + str(len(self.peer_id)))
        handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id
        peers_logger.debug("Sending " + str(handshake) + " to " + self.ip)
        locked_socket_send(handshake)

    def recv_garbage(self, response):
        pass

	def recv_choke(self, response):
		with self.state_lock:
			self.peer_chocking = 1	
		with self.quit_lock:
			self.quit = 1

	def recv_unchoke(self, response):
		with self.state_lock:
			self.choke = 0
		
	def recv_interested(self, response):
		with self.state_lock:
			self.interested = 1

	def recv_have(self, response):
		piece_index = struct.unpack("!I", response[0])
		with self.bitfield_lock:
			self.bitfield.insert(piece_index)

	def recv_bitfield(self, response):
		for i in range(len(response

    def receiver(self, quit_after_one_iteration = None):
        self.quit_lock.acquire()
        while(self.quit != 1):
            self.quit_lock.release()
            response = locked_socket_recv(4)
            peers_logger.debug("Received " + str(response) + " from " + self.ip)
            # Check if response have handshake(1st byte is 19) or other messages
            if response[0] == b'\x13' and response[1:] == b'Bit':
                recv_handshake()
            else:
                length = struct.unpack("!I", response)
                if length == 0:
                    self.recv_keep_alive()
                else:
                    # Receive ID and remaning bytes
                    response = locked_socket_recv(length)
                    fun = {
                            0 : self.recv_choke,
                            1 : self.recv_unchoke,
                            2 : self.recv_interested,
                            3 : self.not_interested,
                            4 : self.recv_have,
                            5 : self.recv_bitfield,
                            6 : self.request,
                            7 : self.recv_piece,
                            8 : self.recv_cancel,
                            9 : self.recv_port
                     }.get(int.from_bytes(response[0], byteorder='little'),
                             self.recv_garbage)(response[1:])
            self.quit_lock.acquire()
			if(quit_after_one_iteration != None):
				break
        self.quit_lock.release()

if __name__ == '__main__':
    ubuntu = torrent_file.torrent_file(sys.argv[1])
    http_tracker = filter_tracker(ubuntu.tracker, 'http')
    print("Http protocol :- ")
    print(http_tracker)
    t = tracker.tracker(http_tracker[0], ubuntu)
