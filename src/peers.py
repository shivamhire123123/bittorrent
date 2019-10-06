import tracker
import torrent_file
import sys
import struct
from socket import *
from torrent_logger import *

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
        # Use to communicate to peer
        self.ip = ip
        self.connection_port = port
        self.socket = None

    def handshake(self, torrent):
        self.pstr = "BitTorrent protocol"
        self.pstrlen = struct.pack("!B", len(self.pstr))
        self.pstr = struct.pack("!" + str(len(self.pstr)) + "s", self.pstr.encode())
        self.reserved = struct.pack("!Q", 0)
        self.info_hash = b''
        print(torrent.info_hash.digest())
        print(torrent.peer_id)
        for i in torrent.info_hash.digest():
            self.info_hash += struct.pack("!B", i)
        self.peer_id = b''
        for i in torrent.peer_id:
            self.peer_id += struct.pack("!B", i)

        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((self.ip, self.connection_port))
        peers_logger.debug("pstrlen - " + str(self.pstrlen))
        peers_logger.debug("pstr - " + str(self.pstr))
        peers_logger.debug("info_hash - " + str(self.info_hash))
        peers_logger.debug("peer_id - " + str(self.peer_id))
        peers_logger.debug("length of info_hash and peer_id is " + str(len(self.info_hash)) + " and " + str(len(self.peer_id)))
        handshake = self.pstrlen + self.pstr + self.reserved + self.info_hash + self.peer_id
        peers_logger.debug("Sending " + str(handshake) + " to " + self.ip)
        self.socket.send(handshake)
        response = self.socket.recv(1024)
        peers_logger.debug("Received " + str(response) + " from " + self.ip)



if __name__ == '__main__':
    ubuntu = torrent_file.torrent_file(sys.argv[1])
    http_tracker = filter_tracker(ubuntu.tracker, 'http')
    print("Http protocol :- ")
    print(http_tracker)
    t = tracker.tracker(http_tracker[0], ubuntu)
