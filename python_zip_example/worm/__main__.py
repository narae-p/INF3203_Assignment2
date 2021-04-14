#!/usr/bin/env python3

import argparse
import http.client
import http.server
import json
import logging
import os
import re
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
from random import choice
from threading import Event, Thread
from urllib.request import urlopen, urlretrieve, Request
from urllib.parse import urlencode
from urllib.error import URLError

worm_host = None

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


# Command-Line Argument Parsing
#=================================================================

def build_arg_parser():
    DIE_AFTER_SECONDS_DEFAULT = 20 * 60
    LOG_LEVEL_DEFAULT = "INFO"
    PORT_DEFAULT = None
    SHUTDOWN_GRACE_PERIOD_DEFAULT = 2

    parser = argparse.ArgumentParser(prog=__file__)

    gate_port_help = "Port number of the wormgate."
    port_help = "Port number of the worm."
    target_size_help = "Target size of the worms."
    source_worm_help = "Source worm host"

    parser.add_argument("-gp", "--gate_port", type=int, help=gate_port_help)
    parser.add_argument("-ts", "--target_size", type=int, help=target_size_help)
    parser.add_argument("-p", "--port", type=int, help=port_help)
    parser.add_argument("-sw", "--source_worm", default="", type=str, help=port_help)

    parser.add_argument("--die-after-seconds", type=float,
        default=DIE_AFTER_SECONDS_DEFAULT,
        help="kill server after so many seconds have elapsed, " +
            "in case we forget or fail to kill it, " +
            "default %d (%d minutes)" % (DIE_AFTER_SECONDS_DEFAULT, DIE_AFTER_SECONDS_DEFAULT/60))
    parser.add_argument("--loglevel", default=LOG_LEVEL_DEFAULT,
        help="Logging level. ERROR, WARN, INFO, DEBUG. Default: {}".format(LOG_LEVEL_DEFAULT))
    parser.add_argument("--shutdown-grace-period", type=float,
        default=SHUTDOWN_GRACE_PERIOD_DEFAULT,
        help="When server is asked to shutdown, give it this many seconds to shutdown cleanly. Default: {}".format(SHUTDOWN_GRACE_PERIOD_DEFAULT))

    return parser

# Logging
#=================================================================

logger = logging.getLogger("worm")

def get_neighbors(host):
    url = 'http://{}/info'.format(host)
    response = urlopen(url)
    string = response.read().decode('utf-8')
    json_obj = json.loads(string)
    other_gates = json_obj['other_gates']
    return other_gates

def get_worm_neighbors(host):
    url = 'http://{}/info'.format(host)
    response = urlopen(url)
    string = response.read().decode('utf-8')
    json_obj = json.loads(string)
    other_worms = json_obj['other_worms']
    return other_worms

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

def spread_worm_segment(target_host, target_size, target_port, source_worm):
    path = os.path.dirname(os.path.realpath(__file__))
    file = open(path, "rb")
    byte = file.read(1)
    data = byte
    while byte:
        byte = file.read(1)
        data += byte
    file.close()

    port = target_host.split(":")[1]
    params = 'args=-gp&args={}&args=-ts&args={}&args=-p&args={}&args=-sw&args={}'.format(port, target_size, target_port, source_worm)
    url = 'http://{}/worm_entrance?{}'.format(target_host, params)

    req = Request(url, data)
    response = urlopen(req)

def start_spread(args):

    hostname = re.sub('\.local$', '', socket.gethostname())
    port = args.port
    gate_port = args.gate_port
    source_worm = args.source_worm
    
    print("gate_port:", gate_port)
    print("port:", port)
    print("source_worm:", source_worm)

    gate_host = hostname + ":" + str(gate_port)
    worm_host = hostname + ":" + str(port)
    target_size = args.target_size

    print("target_size:", target_size)
    print("gate_host:", gate_host)
    print("worm_host:", worm_host)

    neighbors = get_neighbors(gate_host)
    print("neighbors:", neighbors)
    target_neighbor = worm_host
    if len(neighbors) > 0:
        target_neighbor_list = list(filter((lambda neighbor_host: neighbor_host > gate_host), neighbors))
        target_neighbor = neighbors[0] if len(target_neighbor_list) <= 0 else target_neighbor_list[0]
    print("target_neighbor:", target_neighbor)
    target_worm_port = choice([i for i in range(49152, 65535) if i not in [target_neighbor.split(":")[1]]])
    print("target_worm_port:", target_worm_port)
    if target_size <= 0:
        print("Target size is 0, no worm is spawned ")
    elif len(neighbors) == 0:
        # spread(gate_host, target_size, other_gates)
        print("len(neighbors) == 0 ", len(neighbors))
    else:
        if source_worm:
            worm_neighbors = get_worm_neighbors(source_worm)
            if len(worm_neighbors) < (target_size - 1):
                spread_worm_segment(target_neighbor, target_size, target_worm_port, worm_host)
        else:
            spread_worm_segment(target_neighbor, target_size, target_worm_port, worm_host)
    # segements = check_num_of_segments(host, target_size)
    # numsegments = segements[0]
    # gate_segement_size = segements[1]
    # other_gates = segements[2]
    # if target_size == 0:
    #     print("Target size is 0, no worm is spawned ")
    # elif numsegments <= gate_segement_size:
    #     timer = RepeatedTimer(3, spread, host, target_size, other_gates)
    # else:
    #     print("Enough number of worms in this portal (%s), no worm is spawned ", host)

# HTTP Request Handler
#=================================================================

class HttpRequestHandler(http.server.BaseHTTPRequestHandler):

    def send_whole_response(self, code, content, content_type=None):

        if isinstance(content, str):
            content = content.encode("utf-8")
            if not content_type:
                content_type = "text/plain"
            if content_type.startswith("text/"):
                content_type += "; charset=utf-8"
        elif isinstance(content, object):
            content = json.dumps(content, indent=2)
            content += "\n"
            content = content.encode("utf-8")
            content_type = "application/json"

        self.send_response(code)
        self.send_header('Content-type', content_type)
        self.send_header('Content-length',len(content))
        self.end_headers()
        self.wfile.write(content)

    # def do_POST(self):
    #     parsed_path = urllib.parse.urlparse(self.path)
    #     path_path = parsed_path.path
    #     qs = urllib.parse.parse_qs(parsed_path.query)

    #     content_length = int(self.headers.get('content-length', 0))
    #     content = self.rfile.read(content_length)
        
    #     if path_path == "/worm_entrance":
    #         exec_bin = content
    #         exec_args = qs["args"] if "args" in qs else []

    #         wormgatecore.start_process(content, exec_args)

    #         self.send_whole_response(200, "Worm segment uploaded and started\n")
    #         return

    #     elif path_path == "/kill_worms":
    #         global shotdown_flag

    #         wormgatecore.remove_finished()
    #         exitcodes = wormgatecore.cleanup_all()

    #         jsonresp = {
    #                 "msg": "Child processes killed",
    #                 "exitcodes": exitcodes,
    #                 }
    #         self.send_whole_response(200, jsonresp)
    #         return

    #     else:
    #         self.send_whole_response(404, "Unknown path: " + self.path)

    def do_GET(self):
        if self.path == "/info":
            # wormgatecore.remove_finished()
            jsonresp = {
                    "msg": "Worm running",
                    "servername": servername,
                    "other_worms": wormgatecore.other_gates,
            }
            self.send_whole_response(200, jsonresp)
            return

        else:
            self.send_whole_response(404, "Unknown path: " + self.path)

class ThreadingHttpServer(http.server.HTTPServer, socketserver.ThreadingMixIn):
    pass

def run_http_server(args):
    server = ThreadingHttpServer( ('', args.port), HttpRequestHandler)

    logging.basicConfig(level=args.loglevel)
    logger.setLevel(args.loglevel)

    def run_server():
        logger.info("Starting worm on port %d." , args.port)
        server.serve_forever()
        logger.info("Worm has shut down cleanly.")

    # Start HTTP server in a separate thread for proper shutdown
    #
    # serve_forever() and shutdown() must be called from separate threads
    # for the shutdown to work properly.
    # shutdown() is called by signal handlers and by the timeout,
    # which both execute on the main thread.
    # So the server must be running on a separate thread.
    server_thread = threading.Thread(target=run_server)
    # Setting thread as daemon will allow the program to exit even if the server gets hung up.
    server_thread.daemon = True
    server_thread.start()

    def shutdown_server_with_grace_period(thread):
        logger.info("Asking worm to shut down.")
        server.shutdown()
        thread.join(args.shutdown_grace_period)
        if thread.is_alive():
            logger.error("Server thread is still alive after %.3f-second grace period. Trying to exit anyway.", args.shutdown_grace_period)
            sys.exit(1)

    def shutdown_server_on_signal(signum, frame):
        if hasattr(signal, "Signals"):
            signame = signal.Signals(signum).name
            sigdesc = "{}, {}".format(signum, signame)
        else:
            sigdesc = str(signum)
        logger.info("Got system signal %s.", sigdesc)
        shutdown_server_with_grace_period(server_thread)

    # Install signal handlers
    signal.signal(signal.SIGTERM, shutdown_server_on_signal)
    signal.signal(signal.SIGINT, shutdown_server_on_signal)

    # Run until given timeout
    server_thread.join(args.die_after_seconds)

    # Check if server timed out instead of exiting
    if server_thread.is_alive():
        logger.warn("Reached %.3f second timeout.", args.die_after_seconds)
        shutdown_server_with_grace_period(server_thread)

if __name__ == '__main__':
    parser = build_arg_parser()
    args = parser.parse_args()

    start_spread(args)

    run_http_server(args)

