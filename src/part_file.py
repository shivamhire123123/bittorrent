import threading
import struct
from torrent_logger import *
import queue
import collections
import time

class part_file:
    def __init__(self, file_path, file_extract = None):
        '''
        Initializes the synchronus queue and create the a new part file if
        it is not already pass as argument
        Format of part file is as follows:
        piece number
        piece length(to cover last piece size case)
        piece data
        ...
        No partially downloaded pieces will be store in the file
        Pass pieces to the sync queue only after checking the hash
        '''
        # the queue will have list of form [piece_index, data]
        self.file_queue = queue.Queue()
        # this queue should have data in following format
        # [piece index][begin][length]
        self.peer_request_queue = queue.Queue()
        # format - [piece index][begin][length]
        self.peers_piece_queue = queue.Queue()
        self.file = open(file_path, "ba+")
#        if file_extract is not None:
#            self.file.write(struct.pack("I", len(file_extract.keys())))
#            for key in file_extract:
#                self.file.write(struct.pack("I", len(key)))
#                self.file.write(key)
#                self.file.write(struct.pack("I", len(file_extract[key])))
#                self.file.write(file_extract[key])
        self.quit = 0
        self.lock = threading.Lock()

#    def get_torrent_data(self, part_file_path):
#        '''
#        Read torrent related data from .part file and return the file extract
#        as would be return by the bencodepy decode_from_file function
#        '''
#        f = open(part_file_path, "r")
#        file_extract = collections.OrderedDict()
#        number_key_value = f.read(4)
#        number_key_value = struct.unpack("I", number_key_value)
#        for i in range(number_key_value):
#            key_size = f.read(4)
#            key = f.read(key_size)
#            value_size = f.read(4)
#            value = f.read(value_size)
#            file_extract[key] = value
#        f.close()
#        return file_extract


#TODO handle request from sender
    def start_file_writer(self):
        self.lock.acquire()
        while self.quit == 0:
            self.lock.release()
            while not self.file_queue.empty():
                piece = self.file_queue.get()
                file_logger.debug("Found piece " + str(piece[0]) + " writing it to file")
                self.file.write(struct.pack("I", piece[0]))
                self.file.write(struct.pack("I", len(piece[1])))
                self.file.write(piece[1])
                file_logger.info("Written piece " + str(piece[0]) + " into file")
            if not self.peer_request_queue.empty():
                request = self.peer_request_queue.get()
                file_logger.debug("Found piece request for piece " + str(request))
                self.file.seek(0)
                piece_index = self.file.read(4)
                piece_size = self.file.read(4)
                while(piece_size != b''):
                    piece_index = struct.unpack("I", piece_index)[0]
                    piece_size = struct.unpack("I", piece_size)[0]
                    if(piece_index != request[0]):
                        self.file.seek(piece_size, 1)
                        piece_index = self.file.read(4)
                        piece_size = self.file.read(4)
                        if(len(piece_size) == 0):
                            file_logger.error("Didnt find requested piece " + str(request[0]))
                            break
                    else:
                        file_logger.debug("Found piece " + str(piece_index) + " which was requested by peer")
                        self.file.seek(request[1], 1)
                        block = self.file.read(request[2])
                        self.peers_piece_queue.put([request[0], request[1], request[2], block])
                        break
                self.file.seek(0, 2)

            time.sleep(1)
            self.lock.acquire()
        self.lock.release()

def get_piece_data(part_file_path):
    downloaded_pieces = set([])
    try:
        part_file = open(part_file_path, "rb")
    except:
        file_logger.error("Part file " + part_file_path + " do not exist")
        exit()
    piece_index = part_file.read(4)
    piece_size = part_file.read(4)
    while(piece_size):
        piece_index = struct.unpack("I", piece_index)[0]
        piece_size = struct.unpack("I", piece_size)[0]
        file_logger.debug("Found piece " + str(piece_index) + " in part file")
        downloaded_pieces.add(piece_index)
        part_file.seek(piece_size, 1)
        piece_index = part_file.read(4)
        piece_size = part_file.read(4)
    return downloaded_pieces
