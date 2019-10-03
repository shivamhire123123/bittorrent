import logging
from datetime import datetime

'''
    There will be following loggers
    file_logger :- will update about things happening to file e.g.: downloaded size
                    uptil now, piece download, who is downloading, from whom, to whom
                    uploading
    torrent logger :- which piece downloaded, updating peers list, peers, uploaded, downloaded
    tracker_logger :- conncection to tracker, tracker state, error, response, peers
    peers :- handshake, state, state update, download speed, upload speed, which
            requested piece, downloading piece, uploading piece, peer requesting piece,
            message receive, message send
    There will be following handlers
    file :- will print everything upto debug into file
    console :- will print only things needed by user like error and stuff(this is not UI)
    formatter :- see in code
'''

# Creating logger
file_logger = logging.getLogger("File")
file_logger.setLevel(logging.DEBUG)
torrent_logger = logging.getLogger("Torrent")
torrent_logger.setLevel(logging.DEBUG)
tracker_logger = logging.getLogger("Tracker")
tracker_logger.setLevel(logging.DEBUG)
peers_logger = logging.getLogger("Peers")
peers_logger.setLevel(logging.DEBUG)

# Creating handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
# Dont get confuse between downloaded file and logging file they are different
file_handler = logging.FileHandler('bittorrent.log')
file_handler.setLevel(logging.DEBUG)

# Creating formatters
for_user_formatter = logging.Formatter('%(levelname)s - %(message)s')
verbose_formatter = logging.Formatter('%(levelname)s - %(name)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s')
file_handler.setFormatter(verbose_formatter)
console_handler.setFormatter(for_user_formatter)

# Add handler to the logger
file_logger.addHandler(file_handler)
file_logger.addHandler(console_handler)
torrent_logger.addHandler(file_handler)
torrent_logger.addHandler(console_handler)
tracker_logger.addHandler(file_handler)
tracker_logger.addHandler(console_handler)
peers_logger.addHandler(file_handler)
peers_logger.addHandler(console_handler)

# Printing time to differentiate between different instance of program
torrent_logger.debug(str(datetime.now()) + ' BitTorrent program started')
