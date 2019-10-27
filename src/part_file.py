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
        number of key value pairs
        file_extract
            key length
            key
            value length
            value
        piece number
        piece data
        ...
        No partially downloaded pieces will be store in the file
        Pass pieces to the sync queue only after checking the hash
        code:
            take piece from queue write it to file
        write_torrent_info
        '''
        # the queue will have list of form [piece_index, data]
        file_path += ".part"
        self.file_queue = queue.Queue()
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

    def start_file_writer(self):
        self.lock.acquire()
        while self.quit == 0:
            self.lock.release()
            while not self.file_queue.empty():
                piece = self.file_queue.get()
                self.file.write(struct.pack("I", piece[0]))
                self.file.write(piece[1])
                file_logger.info("Written piece " + str(piece[0]) + " into file")
            time.sleep(1)
            self.lock.acquire()
        self.lock.release()
