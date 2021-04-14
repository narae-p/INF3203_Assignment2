#!/usr/bin/env python3

import argparse
import example_module
import http.client
import json
import logging
import os
import pkg_resources
import re
import socket
import subprocess
import time
from threading import Event, Thread
from urllib.request import urlopen, urlretrieve, Request
from urllib.parse import urlencode
from urllib.error import URLError

# Command-Line Argument Parsing
#=================================================================

def build_arg_parser():
    PORT_DEFAULT = None

    parser = argparse.ArgumentParser(prog=__file__)

    porthelp = "Port number of the wormgate."
    target_sizehelp = "Target size of the worms."

    parser.add_argument("-p", "--port", type=int, help=porthelp)
    parser.add_argument("-ts", "--target_size", type=int, help=target_sizehelp)

    return parser

# Logging
#=================================================================

logger = logging.getLogger("worm")
class RepeatedTimer:

    """Repeat `function` every `interval` seconds."""

    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.start = time.time()
        self.event = Event()
        self.thread = Thread(target=self._target)
        self.thread.start()

    def _target(self):
        while not self.event.wait(self._time):
            self.function(*self.args, **self.kwargs)

    @property
    def _time(self):
        return self.interval - ((time.time() - self.start) % self.interval)

    def stop(self):
        self.event.set()
        self.thread.join()

def check_num_of_segments(host, target_size):
    url = 'http://{}/info'.format(host)
    response = urlopen(url)
    string = response.read().decode('utf-8')
    json_obj = json.loads(string)
    other_gates = json_obj['other_gates']
    numsegments = json_obj['numsegments']
    gate_num = len(other_gates) + 1
    segement_size = 1 if target_size < gate_num else int (target_size / gate_num)
    # this_gate_segement_size = int (segement_size + target_size % gate_num)
    # gate_segment_size = this_gate_segement_size if isMain else segement_size
    return (numsegments, segement_size, other_gates)


def spread_segment(host, target_size, other_gates):
    path = os.path.dirname(os.path.realpath(__file__))
    file = open(path, "rb")
    byte = file.read(1)
    data = byte
    while byte:
        byte = file.read(1)
        data += byte
    file.close()

    port = host.split(":")[1]
    params = 'args=-p&args={}&args=-ts&args={}'.format(port, target_size)
    url = 'http://{}/worm_entrance?{}'.format(host, params)

    req = Request(url, data)
    response = urlopen(req)

def spread(host, target_size, other_gates):
    segements = check_num_of_segments(host, target_size)
    numsegments = segements[0]
    this_gate_segement_size = segements[1]
    if numsegments < this_gate_segement_size:
        spread_segment(host, target_size, other_gates)

    num_gates_to_spread = target_size - 1 if target_size - 1 < len(other_gates) else len(other_gates) 
    for g in range(target_size - 1):
        other_segements = check_num_of_segments(other_gates[g], target_size)
        other_numsegments = other_segements[0]
        other_gate_segement_size = other_segements[1]
        other_other_gates = other_segements[2]
        if other_numsegments < other_gate_segement_size:
            spread_segment(other_gates[g], target_size, other_other_gates)

if __name__ == '__main__':
    parser = build_arg_parser()
    args = parser.parse_args()
    hostname = re.sub('\.local$', '', socket.gethostname())
    port = args.port
    host = hostname + ":" + str(port)
    target_size = args.target_size

    segements = check_num_of_segments(host, target_size)
    numsegments = segements[0]
    gate_segement_size = segements[1]
    other_gates = segements[2]
    if target_size == 0:
        print("Target size is 0, no worm is spawned ")
    elif numsegments <= gate_segement_size:
        timer = RepeatedTimer(3, spread, host, target_size, other_gates)
    else:
        print("Enough number of worms in this portal (%s), no worm is spawned ", host)