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
import urllib.parse
from random import choice
from threading import Event, Thread
from urllib.request import urlopen, urlretrieve, Request
from urllib.parse import urlencode
from urllib.error import URLError

worm_host = None
worm_neighbors = []

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
    origin_worm_help = "Origin worm host"

    parser.add_argument("-gp", "--gate_port", type=int, help=gate_port_help)
    parser.add_argument("-ts", "--target_size", type=int, help=target_size_help)
    parser.add_argument("-p", "--port", type=int, help=port_help)
    parser.add_argument("-sw", "--source_worm", default="", type=str, help=source_worm_help)
    parser.add_argument("-ow", "--origin_worm", default="", type=str, help=origin_worm_help)

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

def post_finish_spreading(target_host, source_host):
    url = 'http://{}/done_spreading?last_worm={}'.format(target_host, source_host)
    req = Request(url, method="POST")
    response = urlopen(req)
    return response

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

def spread_worm_segment(target_gate_host, target_size, target_worm_port, source_worm="", origin_worm=""):
    global worm_neighbors
    path = os.path.dirname(os.path.realpath(__file__))
    file = open(path, "rb")
    byte = file.read(1)
    data = byte
    while byte:
        byte = file.read(1)
        data += byte
    file.close()

    hostname = target_gate_host.split(":")[0]
    port = target_gate_host.split(":")[1]
    params = 'args=-gp&args={}&args=-ts&args={}&args=-p&args={}&args=-sw&args={}&args=-ow&args={}'.format(port, target_size, target_worm_port, source_worm, origin_worm)
    url = 'http://{}/worm_entrance?{}'.format(target_gate_host, params)

    req = Request(url, data)
    response = urlopen(req)
    worm_neighbors.append('{}:{}'.format(hostname, target_worm_port))


def start_spread(args):
    global worm_host
    
    hostname = re.sub('\.local$', '', socket.gethostname())
    port = args.port
    gate_port = args.gate_port
    source_worm = args.source_worm
    origin_worm = args.origin_worm

    gate_host = hostname + ":" + str(gate_port)
    worm_host = hostname + ":" + str(port)
    target_size = args.target_size

    gate_neighbors = get_neighbors(gate_host)
    target_neighbor = worm_host
    target_worm_port = port
    if len(gate_neighbors) > 0:
        target_neighbor_list = list(filter((lambda neighbor_host: neighbor_host > gate_host), gate_neighbors))
        target_neighbor = gate_neighbors[0] if len(target_neighbor_list) <= 0 else target_neighbor_list[0]
        target_worm_port = choice([i for i in range(49152, 65535) if i not in [target_neighbor.split(":")[1]]])

    if source_worm:
        worm_neighbors.append(source_worm)
        previous_worm_neighbors = get_worm_neighbors(source_worm)
        if (len(worm_neighbors) + len(previous_worm_neighbors)) < target_size:
            spread_worm_segment(target_neighbor, target_size, target_worm_port, worm_host, origin_worm)
        else:
            post_finish_spreading(origin_worm, worm_host)
            worm_neighbors.append(origin_worm)
    else:
        spread_worm_segment(target_neighbor, target_size, target_worm_port, worm_host, worm_host)

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

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path_path = parsed_path.path
        
        if path_path == "/done_spreading":

            last_worm = re.sub(r'^/done_spreading\?last_worm=([\w:-]+)$', r'\1', self.path)
            logging.debug("in /done_spreading\?last_worm=last_worm:{}".format(last_worm))
            worm_neighbors.append(last_worm)
            self.send_whole_response(200, "Worms done spreading\n")
            return

        elif path_path == "/kill":

            jsonresp = {
                    "msg": "worm {} killed".format(worm_host),
                    "exitcodes": exitcodes,
                    }
            self.send_whole_response(200, jsonresp)
            sys.exit()
            return

        else:
            self.send_whole_response(404, "Unknown path: " + self.path)

    def do_GET(self):
        if self.path == "/info":
            # wormgatecore.remove_finished()
            jsonresp = {
                    "msg": "Worm running",
                    "servername": worm_host,
                    "other_worms": worm_neighbors,
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

    # # Start stabilizer
    # stabilization_thread = threading.Thread(target=stabilization) #####
    # stabilization_thread.daemon = True #####
    # stabilization_thread.start() #####

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
    
    def stabilization(): 
        global stop_requested
        global successor
        global predecessor
        global other_neighbors

        stop_requested = False #####
        while not stop_requested:
            logging.info("Start spreading") ##
            start_spread(args)
            logging.info("After spreading") ##

            time.sleep(2) #

    # Install signal handlers
    signal.signal(signal.SIGTERM, shutdown_server_on_signal)
    signal.signal(signal.SIGINT, shutdown_server_on_signal)

    # Run until given timeout
    server_thread.join(args.die_after_seconds)
    # stabilization_thread.join(args.die_after_seconds)

    # Check if server timed out instead of exiting
    if server_thread.is_alive():
        logger.warn("Reached %.3f second timeout.", args.die_after_seconds)
        shutdown_server_with_grace_period(server_thread)
        
    # if stabilization_thread.is_alive(): #####
    #     stabilization_thread.join() 

if __name__ == '__main__':
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.target_size <= 0:
        print("Target size is 0, no worm is spawned ")
    else:
        start_spread(args)
        run_http_server(args)

