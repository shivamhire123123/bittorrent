import tracker
import torrent_file
import sys
import struct
from socket import *
from torrent_logger import *
import threading
import queue
import select
import time

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
    # TODO for main_peer add them after this line
    # send have field on getting a new piece, did not required to be unchocked
    #
    # TODO (general todo for peer) make an interface of peer class to handle
    # socket
    # It should handle case when we want to create socket and connect to peer
    # and when peer connected to us
    # it should also check if the socket is already created
    # it should also have the functionality of closing down the socket
    def __init__(self, ip, port, torrent):
        # Upload speed of peer averaged so far
        self.upload_speed = None
        # Download speed
        self.download_speed = None
        # To see if handshake has taken place with this peer
        # This will be either set by main_peer before starting sender and receiver thread
        # or will be set by sender thread on the command of receiver
        self.handshake_done = 0

        # 4 state variable for peers
        self.am_chocking = 1
        self.am_interested = 0
        self.peer_chocking = 1
        self.peer_interested = 0
        # Lock for updating peer state
        self.state_lock = threading.Lock()
        # A conditional lock using the above lock
        self.state_cond_lock = threading.Condition(self.state_lock)

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
        self.bitfield = set([])
        self.bitfield_lock = threading.Lock()

        # Queue to send data from receiver to sender
        self.request = queue.Queue()

        # Torrent which this peer is serving to
        self.torrent = torrent

        # This is a list of offset of requested pieces and will be used by
        # sender only
        self.torrent.lock.acquire()
        # TODO think about something to update requested_piece list as other peers
        # download the pieces/block
        self.requested_pieces = self.torrent.downloaded_piece_offset.copy()
        self.torrent.lock.release()
        self.num_requested_pieces = 0

    def locked_socket_send(self, data):
        peers_logger.debug("Sending : " + str(data[:255]) + " to " + str(self.ip))
        l = 0
        while(l < len(data)):
            reader, writer, error = select.select([], [self.socket], [])
            with self.socket_lock:
                l += self.socket.send(data[l:])

    def locked_socket_recv(self, length):
        response = b''
        while len(response) != length:
            reader, writer, error = select.select([self.socket], [], [])
            with self.socket_lock:
                response += self.socket.recv(length - len(response))
        peers_logger.debug("Received : " + str(response[:255]) + " from " + str(self.ip))
        return response

    def handshake(self):
        '''
        Will send a handshake message to the peer only if self.handshake_done is 0
        '''
        if self.handshake_done == 1:
            return
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
        peers_logger.debug("Sending handshake:")
        self.locked_socket_send(handshake)
        self.handshake_done = 1

    def recv_garbage(self, response):
        peers_logger.debug("Received garbage from " + self.ip)
        pass

    # TODO implement this
    def recv_keep_alive(self):
        pass

    def recv_choke(self, response):
        peers_logger.debug("Received choke form " + self.ip)
        with self.state_lock:
            self.peer_chocking = 1
        with self.quit_lock:
            self.quit = 1

    def recv_unchoke(self, response):
        peers_logger.debug("Received unchoke form " + self.ip)
        with self.state_cond_lock:
            self.peer_chocking = 0
            # Awakens the sender thread
            peers_logger.debug("Notifying the sender")
            self.state_cond_lock.notify()
        peers_logger.debug("Successfully notified the sender")

    def recv_interested(self, response):
        peers_logger.debug("Received interested form " + self.ip)
        with self.state_lock:
            self.interested = 1

    def recv_not_interested(self, response):
        peers_logger.debug("Received not_interested form " + self.ip)
        with self.state_lock:
            self.interested = 0

    def recv_have(self, response):
        peers_logger.debug("Received have from " + self.ip)
        piece_index = struct.unpack("!I", response[0])[0]
        with self.bitfield_lock:
            self.bitfield.insert(piece_index)
        with self.torrent.lock:
            self.torrent.piece_freq[piece_index] += 1
        # since it may happen that initially the peer may not have any piece
        # which we need but after some time the peer may have the piece so request
        # sender to again call the rarest_first algorithm to see if we may send
        # any request to the peer
        self.request.put([4])

    def recv_bitfield(self, response):
        peers_logger.debug("Received bitfield")
        for i in range(len(response)):
            bit_pos = 0
            for j in range(8):
                if (response[i] >> j) & 1:
                    piece_number = i * 8 + j
                    self.bitfield.add(piece_number)
                    with self.torrent.lock:
                        self.torrent.piece_freq[piece_number] += 1

    def recv_request(self, response):
        temp = struct.unpack("!III", response)
        piece_id, begin, length = temp[0], temp[1], temp[2]
        peers_logger.debug("Received request from " + self.ip + " of " + str(piece_id)
                        + str(begin) + str(length))
        self.request.put([6, piece_id, begin, length])

    # even if this function is name recv_piece it is intended to receive a piece
    def recv_piece(self, response):
        peers_logger.debug("Received piece from " + self.ip + " of length " +\
                str(len(response)))
        self.request.put([7])
        self.torrent.recv_piece(response)

    def recv_cancel(self, response):
        peers_logger.debug("Received cancel from " + self.ip)
        temp = struct.unpack("!III", response)
        piece_id, begin, length = temp[0], temp[1], temp[2]
        self.request.put([8, piece_id, begin, length])
        # TODO implement cancel fully -> do it after implementing main_peer thread

    def recv_port(self, response):
        peers_logger.debug("port message received from " + self.ip + " which is not supported")

    # use quit_after_one_iteration as an updating mech
    # this can be use in handshake, have
    def receiver(self, quit_after_one_iteration = None):
        self.quit_lock.acquire()
        while(self.quit != 1):
            self.quit_lock.release()
            response = self.locked_socket_recv(4)
            # Check if response have handshake(1st byte is 19) or other messages
            if response[0] == 19 and response[1:] == b'Bit':
                peers_logger.debug("Received handshake, other functionality not implemented")
                response = self.locked_socket_recv(64)
                # request sender to send handshake
                self.request.put([19])
                # self.handshake()
                # quit_after_one_iteration = 1
                # TODO handle the case when some other peer will start the communication
            else:
                length = struct.unpack("!I", response)[0]
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
                     }.get(response[0], self.recv_garbage)(response[1:])
            self.quit_lock.acquire()
            if(quit_after_one_iteration != None):
                break
        self.quit_lock.release()

    def send_request(self, piece_index):
        '''
        Sends a request of piece whose index is piece_index. This function should
        impose the rule that request are send in order i.e. if there are 3 blocks
        within a piece then request for 1st block will be send before 2nd and
        3rd. The request continues block rule is used within peer only. Other
        peers can send block request in any order.
        This function also impose the maximum block size rule and decide
        the block size of the request.
        This sends a request message of 16KB block size or less if the requested
        block is last
        It returns if the request was made or not
        '''
        if self.requested_pieces[piece_index] >= self.torrent.piece_len:
            return 0
        else:
            length = struct.pack("!I", 13)
            identify = struct.pack("!B", 6)
            index = struct.pack("!I", piece_index)
            begin = struct.pack("!I", self.requested_pieces[piece_index])
            remaning = self.torrent.piece_len - self.requested_pieces[piece_index]
            max_request_len = 16 * 2 ** 10
            # if remaning is more than max_request_len request block for max
            if remaning > max_request_len:
                requested_length = max_request_len
            # else remaning
            else:
                requested_length = remaning
            block_length = struct.pack("!I", requested_length)
            peers_logger.debug("Sending piece request:")
            peers_logger.debug("Piece - " + str(piece_index))
            peers_logger.debug("Begin - " + str(self.requested_pieces[piece_index]))
            peers_logger.debug("Block length - " + str(requested_length))
            self.requested_pieces[piece_index] += requested_length
            packet = length + identify + index + begin + block_length
            self.locked_socket_send(packet)
            self.num_requested_pieces += 1
            return 1

    def send_unchock(self):
        self.state_lock.acquire()
        if self.am_chocking == 1:
            length = struct.pack("!I", 1)
            identify = struct.pack("!B", 1)
            packet = length + identify
            peers_logger.debug("Sending unchock")
            self.locked_socket_send(packet)
            self.am_chocking = 0
        self.state_lock.release()

    def send_interested(self):
        self.state_lock.acquire()
        if self.am_interested == 0:
            length = struct.pack("!I", 1)
            identify = struct.pack("!B", 2)
            packet = length + identify
            peers_logger.debug("Sending interested")
            self.locked_socket_send(packet)
            self.am_interested = 1
        self.state_lock.release()

    def send_piece(self, piece_index, piece_begin, piece_length, piece):
        length = struct.pack("!I", 9 + piece_length)
        identify = struct.pack("!B", 7)
        index = struct.pack("!I", piece_index)
        begin = struct.pack("!I", piece_begin)
        block = piece
        packet = length + identify + index + begin + block
        peers_logger.debug("Sending piece " + str(piece_index) + " starting from\
                 " + str(piece_begin) + " of length " + str(piece_length))
        self.locked_socket_send(packet)

    # implement rarest first algorithm(the piece which is rarest and which I do
    # not have and which is not already
    # TODO requested to the same peer, if all pieces are requested atleast once
    # start make request twice and so on)
    # it should also take into account that it is asking pieces by block as such
    # it should remember what all pieces it is trying to download
    # one walkaround would be to make as many request as require to get one full
    # piece but this would be bad if we are requesting only one piece
    # another way would be to keep track of piece in request(i.e. piece for whic
    # request for starting block is already sent)
    def request_rarest_first(self, num_request):
        requestable_pieces = self.torrent.requestable_pieces & self.bitfield
        rare_freq = 0
        rare = []
        request_made = 0
        requestable = 1
        while request_made < num_request:
            rare = self.torrent.rarest(requestable_pieces, rare_freq)
            if len(rare) == 0:
                return request_made
            for i in rare:
                while requestable and request_made < num_request:
                    requestable = self.send_request(i)
                    request_made += requestable
            self.torrent.lock.acquire()
            rare_freq = self.torrent.piece_freq[rare[0]]
            self.torrent.lock.release()

    def sender(self):
        '''
        TODO
        receive inputs from receiver
            send handshake on request from receiver
            send requested piece
            send next request to peer
            call rarest_first on receiving a have message, rarest_first should
            then check if that piece is required and if we can make further
            request
            cancel request from peer
                for this reason we will need a separate queue peer_request
        main_peer inputs
            have message
                cancel message if block related to this piece was requested
        periodically send keep_alive
            implement this using the timer object of threading
        dont send pieces unless interested is received
        '''
        peers_logger.debug("Inside sender")
        self.quit_lock.acquire()
        while(self.quit != 1):
            self.quit_lock.release()

            # TODO check if there is a request from receiver to send handshake
            # or bitfield
            # this messages do not require the client to be in unchock stage

            # TODO for now sending interested immediately later send interested
            # only after knowing that the peer have something to give to us
            # send interested message
            self.send_interested()

            # Send unchock
            self.send_unchock()

            # TODO this is very bad design since if this peer has chocked us
            # then we will wait in this loop for infinite time even if the quit
            # bit is set
            # one thing can be done is to check quit bit within the while not
            # loop
            # Wait for an unchock message
            with self.state_cond_lock:
                while not self.peer_chocking == 0:
                    self.state_cond_lock.wait()
                # if an unchoke is received then we must start requesting block
                # again since even if we had previously requested blocks it will
                # be discarded
                if self.num_requested_pieces < 4:
                    self.request_rarest_first(4 - self.num_requested_pieces) # send how many request are need to be send as argument and it is not necessary that it will send that many request, will return false or 0 if no request can be made TODO in such case(it may be optimistic unchock) dont disconnect main_peer will call to quit if no piece is receive after long time

            # check if there is any request from receiver
            try:
                receiver_request = self.request.get_nowait()
                if receiver_request[0] == 7:
                    self.num_requested_pieces -= 1
                # if there is a request of piece from peer send it to part_file
                elif receiver_request[0] == 6:
                    self.torrent.part_file.peer_reuquest_queue.put(receiver_request[1:])
            except queue.Empty:
                pass
            try:
                requested_piece = self.torrent.part_file.peers_piece_queue.get_nowait()
                self.send_piece(requested_piece[0], requested_piece[1], requested_piece[2], requested_piece[3])
            except queue.Empty:
                pass
            time.sleep(1)
            self.quit_lock.acquire()
        self.quit_lock.release()
        # TODO if quit was called due to chock message do the request are
        # discarded hence take appropriate action
        peers_logger("Exiting from sender")




if __name__ == '__main__':
    ubuntu = torrent_file.torrent_file(sys.argv[1])
    http_tracker = filter_tracker(ubuntu.tracker, 'http')
    print("Http protocol :- ")
    print(http_tracker)
    t = tracker.tracker(http_tracker[0], ubuntu)
