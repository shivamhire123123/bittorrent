from bencodepy import decode_from_file
from torrent_logger import *
import sys
class torrent_file:
    def __init__(self, torrent_file, file_extract = None):
        '''
        Initialise various variables for a torrent.
        torrent_file must be path to .torrent file
        Currently this handles only single file case.
        '''
        if file_extract == None:
            self.file_extract = decode_from_file(torrent_file)
        else:
            self.file_extract = file_extract
        self.tracker = []
        if b'announce-list' in self.file_extract:
            for i in self.file_extract[b'announce-list']:
                self.tracker.append(i[0].decode())
        else:
            self.tracker = [self.file_extract[b'announce'].decode()]
        if b'encoding' in self.file_extract:
            self.encoding = self.file_extract[b'encoding'].decode()
        else:
            self.encoding = 'UTF-8'
        self.piece_len = self.file_extract[b'info'][b'piece length']
        self.piece = self.file_extract[b'info'][b'pieces']
        self.name = self.file_extract[b'info'][b'name'].decode()
        self.length = self.file_extract[b'info'][b'length']
        self.print_file_info()

    def print_file_info(self):
        torrent_logger.debug("Trackers :-")
        for i in self.tracker:
            torrent_logger.debug("\t" + i)
        torrent_logger.debug("Piece length :- " + str(self.piece_len))
#        torrent_logger.debug("Hash :- " + str(self.piece.hex()))
        torrent_logger.debug("Name :- " + self.name)
        torrent_logger.debug("Length :- " + str(self.length))
