import torrent
import requests
import hashlib
import os
from datetime import datetime
import bencodepy
from struct import *
from torrent_logger import *


'''
We have to make class for two types of tracker http and udp
base_tracker will be the base class for class of http_tracker and udp_tracker
then there will be a master tracker class which will use this classes to make
list of trackers http and udp
Trackers have following functionality
    find those trackers where present_time - last_request_on >= min_interval
    request peer list from above tracker and update peers list
the init function will be as follows
    the main tracker init function will be called which will first make two list
    of http(https) and udp trackers
    make an array of objects of http and udp trackers and call there corresponding
    init function
it is not neccessary to connect to all trackers keep a max_num_peers and connect
to trackers until we get max_num_peers
'''
class base_tracker:
    def __init__(self, torrent, url):
        self.url = url
        # This key is private between tracker and client
        # self.key = 0
        # Time before which we shouldnt contact tracker
        self.min_interval = 0
        # ID assign by tracker to client
        self.tracker_id = 0
        self.compact = 0
        self.last_request_on = 0
        # This will denote that if we have "tried" connected to this tracker before and
        # from this we will decide if we need to connect to this tracker again
        self.tracker_state = 0
        # If there was some error while connecting to tracker last time
        # whether to include error details?
        # even if we include error details in the end we will try to connect to
        # peer again. can we take action depending on returned error?
        self.error = 0

        torrent.lock.acquire()

        self.payload = {
                'info_hash': torrent.info_hash.digest(),
                'peer_id' : torrent.peer_id,
                'port' : torrent.port_for_peer,
                'uploaded' : torrent.uploaded,
                'downloaded' : torrent.downloaded,
                'left' : torrent.left,
                'compact' : self.compact,
                }

        torrent.lock.release()


class http_tracker(base_tracker):
    def __init__(self, torrent, url):
        base_tracker.__init__(self, torrent, url)

    def get_peers_from_tracker(self, numwant = 10, state = None):
        self.payload['numwant'] = numwant
        if self.tracker_state == 0 and state == None:
            self.payload['event'] = 'started'
        elif state != None:
            self.payload['event'] = state
        elif event in self.payload:
            del self.payload['event']
        self.tracker_respond = requests.get(self.url, params = self.payload)
        tracker_logger.debug("Content of tracker response " +
                            self.tracker_respond.content)
        self.tracker_respond_content = bencodepy.decode(self.tracker_respond.content)
        #TODO check response to see if it has some errors
        # check compact compatibility and accordingly filtering response
        # if tracker return an error message
        # use try except block for get request refer
        # https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
        # conditionaly set if response was acceptable
        self.tracker_state = 1
        peers = self.tracker_respond_content[b'peers']
        peers_list = []
        for i in range(int(len(peers) / 6)):
            peers_list.append([str(peers[6 * i]) + '.' +
                                    str(peers[6 * i + 1]) + '.' +
                                    str(peers[6 * i + 2]) + '.' +
                                    str(peers[6 * i + 3]),
                                    peers[6 * i + 4] * (2 ** 8) +
                                    peers[6 * i + 5]])

        if b'min interval' in self.tracker_respond_content:
            self.min_interval = self.tracker_respond_content[b'min interval']
        if b'tracker id' in self.tracker_respond_content:
            self.tracker_id = self.tracker_respond_content[b'tracker id']
        self.last_request_on = datetime.now()
        return peers_list

class udp_tracker(base_tracker):
    def __init__(self, torrent, url):
        tracker_logger.error('UDP tracker code not implemented')
        return NotImplemented

class tracker:
    def __init__(self, torrent, tracker_list):
        self.http_tracker = []
        self.udp_tracker = []
        for i in tracker_list:
            if i.find('http') != -1:
                self.http_tracker.append(http_tracker(torrent, i))
            elif i.find('udp') != -1:
                self.udp_tracker.append(udp_tracker(torrent, i))
            else:
                tracker_logger.warning('Found tracker which is neither udp nor http')
        for i in self.http_tracker:
            tracker_logger.debug("Made tracker object for " + i.url)
        for i in self.udp_tracker:
            tracker_logger("Made tracker object for " + i.url)

if __name__ == '__main__':
    bdot = torrent.torrent('./bdot.torrent')
    t = tracker(bdot.tracker[5], bdot)
    print(t.peers_list)
