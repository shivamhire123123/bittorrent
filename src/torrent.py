import logger.py
import torrent_file
import socket
import hashlib
class torrent:
    def __init__(self, torrent_file_path = None, part_file_path = None):
        '''
        Torrent object will be use to store data for torrent overall like downloaded,
        uploaded, left bytes, piece size, number of pieces, peer_id. It can be
        initialize in two ways either using path to a .torrent file(newly created
        torrent) or using already partially downloaded .part file.
        Note :- .part file is nothing but just an extension use to save temporarly
        downloaded file
        '''
        self.uploaded = 0
        self.downloaded = 0
        self.left = 0
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
            # Initialise using extract from torrent file
            torrent_file_extract = torrent_file.torrent_file(torrent_file_path)
            self.file_extract = torrent_file_extract.file_extract
            self.piece_len = torrent_file_extract.piece_len
            self.name = torrent_file_extract.name
            self.length = torrent_file_extract.length
            self.number_of_pieces = self.length / self.piece_len
            self.trackers_list = torrent_file_extract.tracker
        else:
            torrent_logger.error("Either .part or .torrent file must be passed")
        # Make a trackers object from tracker_list
        self.trackers = tracker.tracker(self.trackers_list, self.port_for_peer)
        # If .part file is not present create it
        if (torrent_file_path != None):
