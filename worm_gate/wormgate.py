#!/usr/bin/env python3

import argparse
import atexit
import http.server
import json
import logging
import os
import random
import re
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import time

# Values pulled from environment
#=================================================================

hostname = re.sub('\.local$', '', socket.gethostname())
local_ips = ["127.0.0.1", socket.gethostbyname(hostname)]
servername = None           # set during startup


# Logging
#=================================================================

logger = logging.getLogger("wormgate")


# Command-Line Argument Parsing
#=================================================================

def build_arg_parser():
    PORT_DEFAULT = None
    DIE_AFTER_SECONDS_DEFAULT = 20 * 60
    SHUTDOWN_GRACE_PERIOD_DEFAULT = 2
    LOG_LEVEL_DEFAULT = "INFO"

    parser = argparse.ArgumentParser(prog=__file__)

    porthelp = "Port number to listen on."
    if PORT_DEFAULT:
        portkwargs = { "default": PORT_DEFAULT,
                "help": porthelp + " Default: {}".format(PORT_DEFAULT) }
    else:
        portkwargs = { "required": True,
                "help": porthelp + " Required." }
    parser.add_argument("-p", "--port", type=int, **portkwargs)

    parser.add_argument("--die-after-seconds", type=float,
            default=DIE_AFTER_SECONDS_DEFAULT,
            help="kill server after so many seconds have elapsed, " +
                "in case we forget or fail to kill it, " +
                "default %d (%d minutes)" % (DIE_AFTER_SECONDS_DEFAULT, DIE_AFTER_SECONDS_DEFAULT/60))

    parser.add_argument("--shutdown-grace-period", type=float,
            default=SHUTDOWN_GRACE_PERIOD_DEFAULT,
            help="When server is asked to shutdown, give it this many seconds to shutdown cleanly. Default: {}".format(SHUTDOWN_GRACE_PERIOD_DEFAULT))

    parser.add_argument("--loglevel", default=LOG_LEVEL_DEFAULT,
            help="Logging level. ERROR, WARN, INFO, DEBUG. Default: {}".format(LOG_LEVEL_DEFAULT))

    parser.add_argument("other_gates", nargs="*", type=str,
            help="Other reachable worm gates from this one (host:port pairs)")

    return parser


# Worm Subprocesses
#=================================================================

class WormProcess(object):
    def __init__(self, executable_content, exec_args=[], popen_kwargs={}):

        # Write executable content to temporary file
        self.execfile = tempfile.NamedTemporaryFile(
                dir="/dev/shm",
                prefix="inf3203_worm_assignment_",
                delete=False)

        self.execfile.write(executable_content)

        # Set it to executable
        os.chmod(self.execfile.name, 0o755)
        self.execfile.close()
        logger.info("Wrote executable to %s", self.execfile.name)

        self.cmd = [self.execfile.name] + exec_args
        self.popen_kwargs = {
                "cwd": "/dev/shm",
                "stdout": sys.stdout,
                "stderr": sys.stderr,
                **popen_kwargs,
                }

        self.popen = subprocess.Popen(self.cmd, **self.popen_kwargs)
        logger.info("Started subprocess. PID %d. Command: %s. Popen args: %s.", self.popen.pid, self.cmd, self.popen_kwargs)

    def __str__(self):
        return "WormProcess{{PID={}, cmd={}, popen_kwargs={}}}".format(self.popen.pid, self.cmd, self.popen_kwargs)

    def poll(self):
        return self.popen.poll()

    def cleanup(self):
        poll = self.popen.poll()
        if poll == None:
            logger.info("%s still running, terminating", self)
            self.popen.terminate()
            time.sleep(.05)

        poll = self.popen.poll()
        if poll == None:
            logger.info("%s still running, killing", self)
            self.popen.kill()
            poll = self.popen.wait()

        if os.path.isfile(self.execfile.name):
            logger.info("Removing executable %s", self.execfile.name)
            os.unlink(self.execfile.name)
        else:
            logger.info("Executable already gone %s", self.execfile.name)

        return poll

class WormGateCore:
    def __init__(self, port=None, other_gates=[]):
        global servername
        self.processes = []
        self.lock = threading.Lock()
        self.other_gates = [og for og in other_gates
                if og!=servername and og!="localhost:"+str(port)]

    def start_process(self, content, exec_args, popen_kwargs={}):
        proc = WormProcess(content, exec_args, popen_kwargs)
        with self.lock:
            self.processes.append(proc)

    def remove_finished(self):
        exitcodes = []
        with self.lock:
            filtered = []
            for proc in self.processes:
                poll = proc.poll()
                if poll != None:
                    exitcodes.append(poll)
                    logger.info("Segment has stopped with exit code %s: %s",
                            poll, proc.execfile.name)
                    proc.cleanup()
                    proc.popen.communicate()
                else:
                    filtered.append(proc)
            self.processes = filtered
        return exitcodes

    def cleanup_all(self):
        exitcodes = []
        with self.lock:
            while self.processes:
                proc = self.processes.pop()
                exitcode = proc.cleanup()
                proc.popen.communicate()
                exitcodes.append(exitcode)
        return exitcodes

wormgatecore = None     # Set during startup

@atexit.register
def cleanup_on_exit():
    global wormgatecore
    if wormgatecore:
        logger.info("Cleaning up worm processes at exit")
        wormgatecore.cleanup_all()

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
        qs = urllib.parse.parse_qs(parsed_path.query)

        content_length = int(self.headers.get('content-length', 0))
        content = self.rfile.read(content_length)

        if path_path == "/worm_entrance":
            exec_bin = content
            exec_args = qs["args"] if "args" in qs else []

            wormgatecore.start_process(content, exec_args)

            self.send_whole_response(200, "Worm segment uploaded and started\n")
            return

        elif path_path == "/kill_worms":
            global shotdown_flag

            wormgatecore.remove_finished()
            exitcodes = wormgatecore.cleanup_all()

            jsonresp = {
                    "msg": "Child processes killed",
                    "exitcodes": exitcodes,
                    }
            self.send_whole_response(200, jsonresp)
            return

        else:
            self.send_whole_response(404, "Unknown path: " + self.path)

    def do_GET(self):
        if self.path == "/info":
            wormgatecore.remove_finished()
            jsonresp = {
                    "msg": "Worm gate running",
                    "servername": servername,
                    "numsegments": len(wormgatecore.processes),
                    "other_gates": wormgatecore.other_gates,
            }
            self.send_whole_response(200, jsonresp)
            return

        else:
            self.send_whole_response(404, "Unknown path: " + self.path)


# HTTP Server
#=================================================================

class ThreadingHttpServer(http.server.HTTPServer, socketserver.ThreadingMixIn):
    pass

def run_http_server(args):
    global wormgatecore

    wormgatecore = WormGateCore(args.port, args.other_gates)
    server = ThreadingHttpServer( ('', args.port), HttpRequestHandler)

    logging.basicConfig(level=args.loglevel)
    logger.setLevel(args.loglevel)

    def run_server():
        logger.info("Starting server on port %d." , args.port)
        server.serve_forever()
        logger.info("Server has shut down cleanly.")

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
        logger.info("Asking server to shut down.")
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


# Main
#=================================================================

if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    servername = hostname + ":" + str(args.port)
    logger = logging.getLogger(servername + "-wormgate")

    run_http_server(args)
