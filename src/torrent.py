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

        # Making lock for uploaded, downloaded and left
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
            # This function should initialize torrent variables
            part_file(file_path = part_file_path, torrent = self)
        elif (torrent_file_path != None and part_file_path == None):
            # Initialise using extract from .torrent file
            torrent_file_extract = torrent_file.torrent_file(torrent_file_path)
            self.file_extract = torrent_file_extract.file_extract
            self.piece_len = torrent_file_extract.piece_len
            self.name = torrent_file_extract.name
            self.length = torrent_file_extract.length
            self.number_of_pieces = self.length / self.piece_len
            self.trackers_list = torrent_file_extract.tracker
            self.left = self.length
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

    def get_peers(self, num_of_peers = 20):
        

if __name__ == '__main__':
    tor = torrent(sys.argv[1])

