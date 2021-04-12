#!/usr/bin/env python3

import argparse
import example_module
import http.client
import json
import pkg_resources
import re
import socket
from urllib.request import urlopen

# Command-Line Argument Parsing
#=================================================================

def build_arg_parser():
    PORT_DEFAULT = None

    parser = argparse.ArgumentParser(prog=__file__)

    porthelp = "Port number of the wormgate."

    parser.add_argument("port", type=int, help=porthelp)

    return parser

if __name__ == '__main__':
    parser = build_arg_parser()
    args = parser.parse_args()
    print("args.port", args.port)
    hostname = re.sub('\.local$', '', socket.gethostname())
    print("hostname:", hostname)
    print("Hello, World!")
    print(example_module.MODULE_STRING)
    print(pkg_resources \
            .resource_string("resources", "example_resource.txt") \
            .decode("utf-8"))
    url = 'http://localhost:{}/info'.format(args.port)
    response = urlopen(url)
    string = response.read().decode('utf-8')
    json_obj = json.loads(string)
    print("json_obj:",json_obj)
    other_gates = json_obj['other_gates']
    print("other_gates:",other_gates)
    for gate in other_gates:
        url = 'http://{}/info'.format(gate)
        response = urlopen(url)
        string = response.read().decode('utf-8')
        json_obj = json.loads(string)
        print("other_gates json_obj:",json_obj)

