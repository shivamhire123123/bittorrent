from torrent_logger import *
import torrent_file
from socket import *
import hashlib
import threading
import bencodepy
import part_file
import sys
import os
from datetime import datetime
import tracker
import peers
import struct
import part_file
import random

if __name__ == '__main__':
    if len(sys.argv) == 2:
        tor = torrent(sys.argv[1])
    else:
        tor = torrent(sys.argv[1], sys.argv[2])
    peer_list = [['127.0.0.1', int(sys.argv[3])], ['62.210.209.146', 51413], ['185.44.107.109', 51413],
            ['77.13.17.35', 51413], ['185.203.56.6', 61005], ['82.56.184.243',
                51413], ['110.175.89.172', 6904], ['89.178.161.105', 51413],
            ['144.217.176.169', 9366], ['82.64.50.120', 51413], ['146.0.139.21'
                , 51413]]
    tor.get_peers_from_tracker(10, peer_list = peer_list)
    peer_index = 4
#    tor.peers[peer_index].socket = socket(AF_INET, SOCK_STREAM)
#    tor.peers[peer_index].socket.connect((peer_list[peer_index][0], peer_list[peer_index][1]))
#    tor.peers[peer_index].handshake()
#    tor.peers[peer_index].send_bitfield()
#    peer1_receiver = threading.Thread(None, tor.peers[peer_index].receiver)
#    peer1_sender = threading.Thread(None, tor.peers[peer_index].sender)
#    part_file_thread = threading.Thread(None, tor.part_file.start_file_writer)
#    peer1_receiver.start()
#    peer1_sender.start()
#    part_file_thread.start()
#    peer1_receiver.join()
#    peer1_sender.join()
#    part_file_thread.join()
    num_simul_peers = 10
    peers_obj_list = tor.get_all_peers()
    waiting_handshake_socket = []
    waiting_handshake_peers = []
    passive_peers = []
    for (i in range(len(peers_obj_list))) && connected_peers != num_simul_peers:
        if(peers_obj_list[i].connect() != 0):
            peers_obj_list[i].handshake()
            waiting_handshake_socket.append(peers_obj_list[i])
            waiting_handshake_peers.append(peers_obj_list[i])

    while True:
        readers, writers, errors = select.select(waiting_handshake_socket, [], [], 1)
        if(len(readers) == 0):
            break
        for socket in readers:
            for peer in waiting_handshake_peers:
                if peer.socket == socket:























