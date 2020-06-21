#!/usr/bin/env python3

import socketserver
import argparse
import socket
import struct
import json
import os
from zlib import compress

from providers import get_providers


def get_handler(providers, env):
    class ResponddUDPHandler(socketserver.BaseRequestHandler):
        def multi_request(self, providernames):
            ret = {}
            for name in providernames:
                try:
                    provider = providers[name]
                    ret[provider.name] = provider.call(env)
                except:
                    pass
            return compress(str.encode(json.dumps(ret)))[2:-4]

        def handle(self):
            data = self.request[0].decode('UTF-8').strip()
            print (data)
            socket = self.request[1]
            response = None

            if data.startswith("GET "):
                response = self.multi_request(data.split(" ")[1:])
            else:
                answer = providers[data].call(env)
                if answer:
                    response = str.encode(json.dumps(answer))

            if response:
                socket.sendto(response, self.client_address)

    return ResponddUDPHandler

if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage="""
      %(prog)s -h
      %(prog)s [-c <config-file>]""")
    parser.add_argument('-c', dest='config_file',
                        default="/etc/respondd/bat0.json", metavar='<config-file>',
                        help='config file in JSON format (default: /etc/respondd/bat0.json)')
    args = parser.parse_args()

    with open(args.config_file, 'r') as f:
        config = json.load(f)

    socketserver.ThreadingUDPServer.address_family = socket.AF_INET6
    server = socketserver.ThreadingUDPServer(
        (config['iface'], config['port']),
        get_handler(get_providers(config['directory']), {'batadv_dev': config['batadv_iface'], 'mesh_ipv4': config['mesh_ipv4']})
    )
    server.daemon_threads = True

    if config['mcast_ifaces']:
        mcast_ifaces = { ifname: group for ifname, group, *_
                        in [ reversed([ config['group'] ] + ifspec.split('%')) for ifspec
                         in config['mcast_ifaces'] ] }

        for (inf_id, inf_name) in socket.if_nameindex():
            if inf_name in mcast_ifaces:
                group_bin = socket.inet_pton(socket.AF_INET6, mcast_ifaces[inf_name])
                mreq = group_bin + struct.pack('@I', inf_id)
                server.socket.setsockopt(
                    socket.IPPROTO_IPV6,
                    socket.IPV6_JOIN_GROUP,
                    mreq
                )

    server.serve_forever()
