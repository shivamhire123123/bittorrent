from torrent_logger import *
import torrent_file
from socket import *
import hashlib
import threading
import bencodepy
import part_file
import sys
import os
from datetime import datetime
import tracker
import peers

class torrent:
    def __init__(self, torrent_file_path = None, part_file_path = None):
        '''
        Torrent object will be use to store data for torrent overall like downloaded,
        uploaded, left bytes, piece size, number of pieces, peer_id. It can be
        initialize in two ways either using path to a .torrent file(newly created
        torrent) or using already partially downloaded .part file.
        Note :- .part file is nothing but just an extension use to save temporarly
        downloaded file
        This function is not thread safe
        '''
        # Will be access by both tracker thread and peer thread hence need to be locked
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
        self.piece_freq = None
        self.my_bitfield = set([])
        # This list will store the count of number of request in pipeline for
        # corresponding piece
        self.requested_pieces = None
        # This array will store offset of pieces below which blocks are already
        # downloaded
        self.downloaded_piece_offset = None
        # This denotes piece which this client do not have
        self.requestable_pieces = set([])
        # Making lock for my_bitfield, piece_freq, uploaded, downloaded and left
        self.lock = threading.Lock()

        # Creating peer id
        self.peer_id = 0
        peer_id_sha = hashlib.sha1()
        peer_id_sha.update(str(os.getpid()).encode())
        peer_id_sha.update(str(datetime.now()).encode())
        self.peer_id = peer_id_sha.digest()

        # Creating TCP socket to accept connections from other peers
        self.socket_for_peer = socket(AF_INET, SOCK_STREAM)
        self.port_for_peer = self.socket_for_peer.getsockname()[1]

        # If there is already downloaded file read information from it
        if (part_file_path != None and torrent_file_path == None):
            torrent_logger.debug("Reading torrent info from part file " + part_file_path)
            # This function should initialize all torrent variables
            part_file(file_path = part_file_path, torrent = self)
        elif (torrent_file_path != None and part_file_path == None):
            # Initialise using extract from .torrent file
            torrent_file_extract = torrent_file.torrent_file(torrent_file_path)
            self.file_extract = torrent_file_extract.file_extract
            self.piece_len = torrent_file_extract.piece_len
            self.name = torrent_file_extract.name
            self.length = torrent_file_extract.length
            self.number_of_pieces = int(self.length / self.piece_len)
            self.trackers_list = torrent_file_extract.tracker
            self.left = self.length
            # Initialize all downloaded offset to zero since this is a new torrent
            # download
            self.lock.acquire()
            self.downloaded_piece_offset = [0] * self.number_of_pieces
            self.lock.release()
        else:
            torrent_logger.error("Either of .part or .torrent file must be passed")

        self.info_hash = hashlib.sha1()
        info_bencode = self.file_extract[b'info']
        self.info_hash.update(bencodepy.encode(info_bencode))

        # Make a trackers object from tracker_list
        self.trackers = tracker.tracker(self, self.trackers_list)

        # If .part file is not present create it
        if (torrent_file_path != None):
            torrent_logger.error(".part file code not implemented")

        self.lock.acquire()
        self.piece_freq = [0] * self.number_of_pieces
        self.requested_pieces = [0] * self.number_of_pieces
        for i in range(self.number_of_pieces):
            if i not in self.my_bitfield:
                self.requestable_pieces.add(i)
        self.lock.release()


    def get_peers(self, num_of_peers = 20, peer_list = None):
        if peer_list == None:
            self.peer_list = []
            temp_list = []
            for tracker in self.trackers.http_tracker:
                temp_list = tracker.get_peers_from_tracker(num_of_peers)
                torrent_logger.debug("Got " + str(len(temp_list)) + " peers")
                self.peer_list += temp_list
                num_of_peers -= len(temp_list)
                torrent_logger.debug(str(num_of_peers) + " peers remaning")
                if num_of_peers <= 0:
                    num_of_peers = 0
                    break
        else:
            self.peer_list = peer_list
        self.peers = []
        for peer in self.peer_list:
            self.peers.append(peers.peers(peer[0], peer[1], self))


    # even if this function is name recv_piece it is intended to receive a piece
    # this function will be called by receivers of peers
    def recv_piece(self, response):
        # TODO handle recv_piece
        # TODO update my_bitfield
        # TODO tell all peer sender to send a have message
        # TODO update downloaded_offset ignore if that block with in a piece
        # is already downloaded, append half downloaded block etc
        return NotImplemented

    # This will see the freq of each piece in the swarn and return the list of
    # piece which are rarest
    def rarest(self, requestable, greater_than):
        '''
        This function returns a list of pieces from requestable which have minimum
        frequencey which itself is more than greater_than
        '''
        rare = []
        rare_freq = min(self.piece_freq[i] for i in requestable \
                if self.piece_freq[i] > greater_than)
        for piece in requestable:
            if self.piece_freq[piece] == rare_freq:
                rare.append(piece)

        return rare

if __name__ == '__main__':
    tor = torrent(sys.argv[1])
    peer_list = [['62.210.209.146', 51413], ['185.44.107.109', 51413],
            ['77.13.17.35', 51413], ['185.203.56.6', 61005], ['82.56.184.243',
                51413], ['110.175.89.172', 6904], ['89.178.161.105', 51413],
            ['144.217.176.169', 9366], ['82.64.50.120', 51413], ['146.0.139.21'
                , 51413]]
    tor.get_peers(10, peer_list = peer_list)
    tor.peers[1].socket = socket(AF_INET, SOCK_STREAM)
    tor.peers[1].socket.connect((peer_list[1][0], peer_list[1][1]))
    tor.peers[1].handshake()
    peer1_receiver = threading.Thread(None, tor.peers[1].receiver)
    peer1_sender = threading.Thread(None, tor.peers[1].sender)
    peer1_receiver.start()
    peer1_sender.start()
    peer1_receiver.join()
    peer1_sender.join()
