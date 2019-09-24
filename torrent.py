from bencodepy import decode_from_file
class torrent:
    def __init__(self, torrent_file):
        '''
        Initialise various variables for a torrent.
        torrent_file must be path to .torrent file
        Currently this handles only single file case.
        '''
        self.file_extract = decode_from_file(torrent_file)
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

    def print_file_info(self):
        print("Trackers :-")
        for i in self.tracker:
            print("\t" + i)
        print("Piece length :- " + str(self.piece_len))
        print("Hash :- " + str(self.piece.hex()))
        print("Name :- " + self.name)
        print("Length :- " + str(self.length))

if __name__ == '__main__':
    bdot = torrent('./bdot.torrent')
    bdot.print_file_info()
