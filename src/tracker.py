import torrent
import requests
import hashlib
import os
from datetime import datetime
import bencodepy
from struct import *

class tracker:
    def __init__(self, url, torrent, port):
        self.url = url
        info_hash = hashlib.sha1()
        peer_id = hashlib.sha1()
        info_bencode = torrent.file_extract[b'info']
        info_hash.update(bencodepy.encode(info_bencode))
        self.payload = {
                'info_hash': info_hash.digest(),
                'peer_id' : torrent.peer_id,
                'port' : port,
                'uploaded' : torrent.uploaded,
                'downloaded' : 0,
                'left' : torrent.length,
                'compact' : 1,
                'event' : 'started',
                }
        self.tracker_respond = requests.get(url, params = self.payload)
        self.tracker_respond = bencodepy.decode(self.tracker_respond.content)
        self.peers = self.tracker_respond[b'peers']
        self.peers_list = []
        for i in range(int(len(self.peers) / 6)):
            self.peers_list.append([str(self.peers[6 * i]) + '.' +
                                    str(self.peers[6 * i + 1]) + '.' +
                                    str(self.peers[6 * i + 2]) + '.' +
                                    str(self.peers[6 * i + 3]),
                                    self.peers[6 * i + 4] * (2 ** 8) +
                                    self.peers[6 * i + 5]])


if __name__ == '__main__':
    bdot = torrent.torrent('./bdot.torrent')
    t = tracker(bdot.tracker[5], bdot)
    print(t.peers_list)
