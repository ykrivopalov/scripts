#!/bin/python

"""Script that simplify access to remote host.
Can mount smb shares, mount by ssh, generate scripts for rdp and ssh access.
Depends on pass, xfreerdp"""

import argparse
import getpass
import os
import re
import socket
import subprocess

HOME_DIR = os.path.expanduser('~')
RESOLUTION = '1366x728'

SSH = 22
SMB = 445
RDP = 3389


def _is_port_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((host, port))
    if result == 0:
        return True

    print('{}:{} is unaccessible'.format(host, port))


def _parse_uri(uri):
    match = re.match('(.*)@(.*)', uri)
    return match.group(1), match.group(2)


def _read_credentials_script(host):
    return ['IFS=":" read USERNAME PASSWORD << EOF',
            '`pass show tmp/{}`'.format(host),
            'EOF']


def _rdp_script(host, title):
    title = '{} ({})'.format(title, host)
    return '\n'.join(
        ['#!/bin/sh'] +
        _read_credentials_script(host) +
        ['xfreerdp -grab-keyboard +clipboard /size:{} /v:{}'
         ' /drive:develop,/home/yk/Develop /u:$USERNAME /p:$PASSWORD'
         ' /cert-ignore /t:"{}" &'.format(RESOLUTION, host, title)]
    )


def _ensure_dir_of_file(path):
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def _make_rdp_script(host, title):
    script_path = '{}/rdp/{}.sh'.format(HOME_DIR, title)
    _ensure_dir_of_file(script_path)
    with open(script_path, 'w') as rdp_sh:
        rdp_sh.write(_rdp_script(host, title))
    os.system('chmod +x ' + script_path)


def _link_smb(host, title):
    source = '/smb/{}'.format(host)
    target = HOME_DIR + '/mnt/' + title
    os.system('rm {}'.format(target))
    os.system('ln -s {} {}'.format(source, target))


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('uri', help='uri of machine to addition')
    parser.add_argument('title', help='title of machine')
    args = parser.parse_args()

    machine = args.uri
    title = args.title

    user, host = _parse_uri(machine)
    password = getpass.getpass()

    secret = user + ':' + password
    secret = secret + '\n' + secret + '\n'
    subprocess.run(
        ['pass', 'insert', '-f', 'tmp/' + host],
        input=secret, universal_newlines=True)

    if _is_port_open(host, SMB):
        print("setting up SMB")
        _link_smb(host, title)

    if _is_port_open(host, RDP):
        print("setting up RDP")
        _make_rdp_script(host, title)


_main()
