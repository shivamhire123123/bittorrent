import torrent
import select
import socket
import threading

receiver_peer_port = 12001
tor = torrent.torrent(sys.argv[1], sys.argv[2])
connectionsocket, address = tor.socket_for_peer.accept()
tor.add_peer(address[0], address[1])
peer = tor.get_random_peer()
peer.socket = connectionsocket
peer.handshake()
peer_receiver = threading.Thread(None, peer.receiver)
peer_sender = threading.Thread(None, peer.sender)
peer_file = threading.Thread(None, tor.part_file.start_file_writer)
peer_receiver.start()
peer_sender.start()
peer_file.start()
