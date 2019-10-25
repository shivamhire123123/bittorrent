import tracker
import torrent_file
import sys
import struct
from socket import *
from torrent_logger import *
import threading
import queue

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
    # TODO make an interface of peer class to handle socket
    # It should handle case when we want to create socket and connect to peer
    # and when peer connected to us
    # it should also check if the socket is already created
    # it should also have the functionality of closing down the socket
    def __init__(self, ip, port, torrent):
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
        # This socket object will be made by main_peer thread since it will be
        # point less to create it here, it will just use up number of sockets
        # available with OS without doing some actual use of them

        # This variable is set by main_peer_thread, receiver_thread or sender_thread
        # to notify other thread to shutdown
        self.quit = 0
        self.quit_lock = threading.Lock()

        # bitfield set having those piece numbers which the peer have, starts from 0
        self.bitfield = {}
        self.bitfield_lock = threading.Lock()

        # Queue to send data from receiver to sender
        self.request = queue.Queue()

        # Torrent which this peer is serving to
        self.torrent = torrent

    def locked_socket_send(self, data):
        l = 0
        with self.socket_lock:
            while(l < len(data)):
                l += self.socket.send(data[l:])

    def locked_socket_recv(self, length):
        response = b''
        with self.socket_lock:
            while len(response) != response:
                response += self.socket.recv(length - len(response))
        return response

    def handshake(self):
        '''
        Will send a handshake message to the peer
        '''
        self.pstr = "BitTorrent protocol"
        self.pstrlen = struct.pack("!B", len(self.pstr))
        self.pstr = struct.pack("!" + str(len(self.pstr)) + "s", self.pstr.encode())
        self.reserved = struct.pack("!Q", 0)
        self.info_hash = b''
        for i in self.torrent.info_hash.digest():
            self.info_hash += struct.pack("!B", i)
        self.peer_id = b''
        for i in self.torrent.peer_id:
            self.peer_id += struct.pack("!B", i)

        peers_logger.debug("pstrlen - " + str(self.pstrlen))
        peers_logger.debug("pstr - " + str(self.pstr))
        peers_logger.debug("info_hash - " + str(self.info_hash))
        peers_logger.debug("peer_id - " + str(self.peer_id))
        peers_logger.debug("length of info_hash and peer_id is " + str(len(self.info_hash)) + " and " + str(len(self.peer_id)))
        handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id
        peers_logger.debug("Sending " + str(handshake) + " to " + self.ip)
        self.locked_socket_send(handshake)

    def recv_garbage(self, response):
        peers_logger("Received garbage from " + self.ip)
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

    def recv_not_interested(self, response):
        with self.state_lock:
            self.interested = 0

    def recv_have(self, response):
        piece_index = struct.unpack("!I", response[0])
        with self.bitfield_lock:
            self.bitfield.insert(piece_index)
        with self.torrent.lock:
            self.torrent.piece_freq[piece_index] += 1

    def recv_bitfield(self, response):
        peers_logger.debug("Received bitfield")
        for i in range(len(response)):
            bit_pos = 0
            for j in range(8):
                if (response[i] >> j) & 1:
                    piece_number = i * 8 + j
                    self.bitfield.append(piece_number)
                    with self.torrent.lock:
                        self.torrent.piece_freq[piece_number] += 1

    def recv_request(self, response):
        piece_id, begin, length = struct.unpack("!III", response)
        piece_logger("Received request from " + self.ip + " of " + str(piece_id)
                        + str(begin) + str(length))
        self.request.put((6, piece_id, begin, length))

    def recv_piece(self, response):
        piece_logger("Received piece :- " + str(response))
        piece_logger("Receive piece not fully implemented")
        self.request.put((7))
        # TODO handle recv_piece

    def recv_cancel(self, response):
        piece_logger("Received cancel from " + self.ip)
        piece_id, begin, length = struct.unpack("!III", response)
        self.request.put((8, piece_id, begin, length))
        # TODO implement cancel fully -> do it after implementing main_peer thread

    def recv_port(self, response):
        piece_logger("port message received from " + self.ip + " which is not supported")

    def receiver(self, quit_after_one_iteration = None):
        self.quit_lock.acquire()
        while(self.quit != 1):
            self.quit_lock.release()
            response = self.locked_socket_recv(4)
            peers_logger.debug("Received " + str(response) + " from " + self.ip)
            # Check if response have handshake(1st byte is 19) or other messages
            if response[0] == b'\x13' and response[1:] == b'Bit':
                self.handshake()
                quit_after_one_iteration = 1
                # TODO handle the case when some other peer will start the communication
            else:
                length = struct.unpack("!I", response)
                if length == 0:
                    self.recv_keep_alive()
                else:
                    # Receive ID and remaning bytes
                    response = self.locked_socket_recv(length)
                    {
                            0 : self.recv_choke,
                            1 : self.recv_unchoke,
                            2 : self.recv_interested,
                            3 : self.recv_not_interested,
                            4 : self.recv_have,
                            5 : self.recv_bitfield,
                            6 : self.recv_request,
                            7 : self.recv_piece,
                            8 : self.recv_cancel,
                            9 : self.recv_port
                     }.get(int.from_bytes(response[0], byteorder='little'),
                             self.recv_garbage)(response[1:])
            self.quit_lock.acquire()
            if(quit_after_one_iteration != None):
                break
        self.quit_lock.release()

    def sender(self):
        '''
        TODO
        implement rarest first algorithm
        receive inputs from receiver
        check quit bit
        keep atleast x request in pipeline
        '''




if __name__ == '__main__':
    ubuntu = torrent_file.torrent_file(sys.argv[1])
    http_tracker = filter_tracker(ubuntu.tracker, 'http')
    print("Http protocol :- ")
    print(http_tracker)
    t = tracker.tracker(http_tracker[0], ubuntu)
