import os
import re
import argparse
import json
import socket
import time

CONFIG_TEMPLATES_ROOT_PATH = '/config-templates/'
CONFIG_OUTPUT_ROOT_PATH = '/config/'

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = re.sub('[^-a-zA-Z0-9_.]+', '', value)

    return value

def str2bool(v:str):
    """Converts string to boolean"""
    return v.lower() in ('yes', 'true', 't', '1')

def save_json(path:str, data):
	with open(path, 'w') as outfile:
		json.dump(data, outfile, indent=1)

def load_json(path:str):
    with open(path, 'r') as inputfile:
        return json.load(inputfile)

def init_args():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Cardano Configurator')
    parser.add_argument('--node-port', dest='node_port', help='Port of node. Defaults to 3000.', type=int, default=os.environ.get('NODE_PORT', 3000))
    parser.add_argument('--node-name', dest='name', help='Name of node. Defaults to node1.', type=slugify, default=os.environ.get('NODE_NAME', 'node1'))
    parser.add_argument('--node-topology', dest='topology', help='Topology of the node. Should be comma separated for each individual node to add, on the form: <ip>:<port>/<valency>. So for example: 127.0.0.1:3001/1,127.0.0.1:3002/1.', type=str, default=os.environ.get('NODE_TOPOLOGY', ''))
    parser.add_argument('--node-relay', dest='relay', help='Set to 1 if default IOHK relay should be added to the network topology.', type=str2bool, default=os.environ.get('NODE_RELAY', False))
    parser.add_argument('--cardano-network', dest='network', help='Carano network to use (main, test, pioneer). Defaults to main.', type=str, default=os.environ.get('CARDANO_NETWORK', 'main'))
    parser.add_argument('--ekg-port', dest='ekg_port', help='Port of EKG monitoring. Defaults to 12788.', type=int, default=os.environ.get('EKG_PORT', 12788))
    parser.add_argument('--prometheus-port', dest='prometheus_port', help='Port of Prometheus monitoring. Defaults to 12798.', type=int, default=os.environ.get('PROMETHEUS_PORT', 12798))
    parser.add_argument('--resolve-hostnames', dest='resolve_hostnames', help='Resolve hostnames in topology to IP-addresses.', type=str2bool, default=os.environ.get('RESOLVE_HOSTNAMES', False))
    parser.add_argument('--replace-existing', dest='replace_existing', help='Replace existing configs.', type=str2bool, default=os.environ.get('REPLACE_EXISTING_CONFIG', False))  
    args = parser.parse_args()

    # Init network specific paths
    args.CONFIG_TEMPLATES_PATH = os.path.join(CONFIG_TEMPLATES_ROOT_PATH, args.network)
    args.CONFIG_OUTPUT_PATH = os.path.join(CONFIG_OUTPUT_ROOT_PATH, args.network, args.name)
    args.GENESIS_PATH = os.path.join(args.CONFIG_OUTPUT_PATH, 'genesis.json')
    args.TOPOLOGY_PATH = os.path.join(args.CONFIG_OUTPUT_PATH, 'topology.json')
    args.CONFIG_PATH = os.path.join(args.CONFIG_OUTPUT_PATH, 'config.json')

    return args

def init_folder(args):
    """Creates network/node config folders"""
    if not os.path.exists(args.CONFIG_OUTPUT_PATH):
        os.makedirs(args.CONFIG_OUTPUT_PATH)

def init_genesis(args):
    """Initializes the genesis file"""

    INPUT_PATH = os.path.join(args.CONFIG_TEMPLATES_PATH, 'genesis.json')

    if not os.path.exists(args.GENESIS_PATH) or args.replace_existing:
        print('Generating new genesis file %s from template %s' % (args.GENESIS_PATH, INPUT_PATH))

        data = load_json(INPUT_PATH)
        save_json(args.GENESIS_PATH, data)

def resolve_hostname(hostname, tries=0):
    """Resolve IP from hostname"""
    try:
        return socket.gethostbyname(hostname)
    except:
        if tries<10:
            time.sleep(1)

            return resolve_hostname(hostname, tries=tries+1)
        else:
            return hostname

def parse_topology_str(s) -> list:
    """Parses node-topology string and returns list of dicts"""
    topology = []

    if s:
        for a in s.split(','):
            (ip_port, valency) = a.split('/')
            (ip, port) = ip_port.split(':')

            if resolve_hostname: ip = resolve_hostname(ip)

            topology.append({
                'addr': str(ip),
                'port': int(port),
                'valency': int(valency)
            })

    return topology


def init_topology(args):
    """Initializes the topology file"""

    INPUT_PATH = os.path.join(args.CONFIG_TEMPLATES_PATH, 'topology.json')

    if not os.path.exists(args.TOPOLOGY_PATH) or args.replace_existing:
        print('Generating new topology %s from template %s' % (args.TOPOLOGY_PATH, INPUT_PATH))
        print('Topology: ', args.topology)

        data = load_json(INPUT_PATH)

        # Parse topology string
        topology = parse_topology_str(args.topology)

        # Add default IOHK relay
        if args.relay:
            relay = load_json(os.path.join(args.CONFIG_TEMPLATES_PATH, 'relay.json'))
            topology.append(relay)

        data['Producers'] = topology
        save_json(args.TOPOLOGY_PATH, data)

def init_config(args):
    """Initializes the config file"""

    INPUT_PATH = os.path.join(args.CONFIG_TEMPLATES_PATH, 'config.json')

    if not os.path.exists(args.CONFIG_PATH) or args.replace_existing:
        print('Generating new config file %s from template %s' % (args.CONFIG_PATH, INPUT_PATH))

        data = load_json(INPUT_PATH)
        data['GenesisFile'] = args.GENESIS_PATH
        data['hasEKG'] = args.ekg_port
        data['hasPrometheus'] = ['127.0.0.1', args.prometheus_port]
        save_json(args.CONFIG_PATH, data)


if __name__ == '__main__':
    args = init_args()

    init_folder(args)
    init_genesis(args)
    init_topology(args)
    init_config(args)
