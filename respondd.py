#!/usr/bin/env python3

import metasocketserver
import socketserver
import argparse
import socket
import struct
import json
import os
from zlib import compress

from providers import get_providers,Provider
import util

def get_handler(providers, batadv_ifaces, batadv_mesh_ipv4_overrides, env):
    class ResponddUDPHandler(socketserver.BaseRequestHandler):
        def multi_request(self, providernames, local_env):
            ret = {}
            for name in providernames:
                try:
                    provider = providers[name]
                    ret[provider.name] = provider.call(local_env)
                except:
                    pass
            return compress(str.encode(json.dumps(ret)))[2:-4]

        def handle(self):
            data = self.request[0].decode('UTF-8').strip()
            print("From:    {}".format(self.client_address))
            print("Request: {}".format(data))
            socket = self.request[1]
            ifindex = self.request[2]
            response = None

            # Find batman interface the query belongs to
            batadv_dev = util.ifindex_to_batiface(ifindex, batadv_ifaces)
            if batadv_dev == None:
                return

            # Clone global environment and populate with interface-specific data
            local_env = dict(env)
            local_env['batadv_dev'] = batadv_dev
            if batadv_dev in batadv_mesh_ipv4_overrides:
                local_env['mesh_ipv4'] = batadv_mesh_ipv4_overrides[batadv_dev]

            if data.startswith("GET "):
                response = self.multi_request(data.split(" ")[1:], local_env)
            else:
                answer = providers[data].call(local_env)
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

    # Read domain-codes from file
    # known_codes = util.read_domainfile(args.domain_code_file)
    known_codes = config['domaincodes']

    # Extract batman interfaces from commandline parameters
    # and overwrite domain-codes from file with commandline arguments
    batadv_mesh_ipv4_overrides = { }
    batadv_ifaces = [ ]

    for ifspec in config['batadv_ifaces']:
        iface, *left_over = ifspec.split(':')
        batadv_ifaces.append(iface)
        try:
            # if left_over list is not empty, there is at least an override address
            possible_override = left_over.pop(0)
            # this clause is necessary in case one does not specify an ipv4 override, but a domain-code
            if '' != possible_override:
                batadv_mesh_ipv4_overrides[iface] = possible_override
            # if left_over list is not empty, there is a domain_code
            known_codes[iface] = left_over.pop(0)
        except IndexError:
            continue

    global_handler_env = { 'domain_code': config['domain_code'], 'known_codes': known_codes, 'mesh_ipv4': config['mesh_ipv4'] }
    
    metasocketserver.MetadataUDPServer.address_family = socket.AF_INET6
    metasocketserver.MetadataUDPServer.allow_reuse_address = True
    oProviders = get_providers(config['directory'])
    server = metasocketserver.MetadataUDPServer(
        ("", config['port']),
        get_handler(oProviders, batadv_ifaces, batadv_mesh_ipv4_overrides, global_handler_env)
    )
    print("respondd server created.\nProviders")
    for p in oProviders:
        print('\t', oProviders[p].name)
        
    server.daemon_threads = True

    def join_group(mcast_group, if_index=0):
        group_bin = socket.inet_pton(socket.AF_INET6, mcast_group)
        mreq = group_bin + struct.pack('@I', if_index)
        server.socket.setsockopt(
            socket.IPPROTO_IPV6,
            socket.IPV6_JOIN_GROUP,
            mreq
        )

    # Extract multicast interfaces from commandline parameters
    mcast_iface_groups = { }
    for ifspec in config['mcast_ifaces']:
        iface, *groups = reversed(ifspec.split('%'))
        # Populate with default link and site mcast groups if entry not yet created
        if not iface in mcast_iface_groups:
            mcast_iface_groups[iface] = [ group for group in [ config['link_group'], config['site_group'] ] if len(group) > 0 ]
        # Append group specified on commndline
        mcast_iface_groups[iface] += groups

    for (if_index, if_name) in socket.if_nameindex():
        # Check if daemon should listen on interface
        if if_name in mcast_iface_groups:
            groups = mcast_iface_groups[if_name]
            # Join all multicast groups specified for this interface
            for group in groups:
                join_group(group, if_index)

    server.serve_forever()
