#!/bin/python

# Script that simplify access to remote host.
# Can mount smb shares, mount by ssh, generate scripts for rdp and ssh access.
# Depends on secret-tool, autofs, sshpass, xfreerdp

import argparse
import getpass
import os
import re
import socket
import subprocess

HOME_DIR = os.path.expanduser('~')
RESOLUTION = '1920x1040'

SSH = 22
SMB = 445
RDP = 3389


def is_port_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    return result == 0


def parse_uri(uri):
    match = re.match('(.*)@(.*)', uri)
    return match.group(1), match.group(2)


def read_credentials_script(host):
    return ['IFS=":" read USERNAME PASSWORD << EOF',
            '`secret-tool lookup target {}`'.format(host),
            'EOF']


def rdp_script(host, title):
    title = '{} ({})'.format(title, host)
    return '\n'.join(
        ['#!/bin/sh'] +
        read_credentials_script(host) +
        ['xfreerdp -grab-keyboard +clipboard /size:{} /v:{}'
         ' /drive:develop,/home/yk/Develop /u:$USERNAME /p:$PASSWORD'
         ' /cert-ignore /t:"{}" &'.format(RESOLUTION, host, title)]
    )


def ensure_dir_of_file(path):
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def make_rdp_script(host, title):
    script_path = '{}/rdp/{}.sh'.format(HOME_DIR, title)
    ensure_dir_of_file(script_path)
    with open(script_path, 'w') as rdp_sh:
        rdp_sh.write(rdp_script(host, title))
    os.system('chmod +x ' + script_path)


def rpc_script(host):
    return '\n'.join(
        ['#!/bin/sh'] +
        read_credentials_script(host) +
        ['for SERVICE in ${@:2}',
         'do net rpc service $1 $SERVICE -I {} -U $USERNAME%$PASSWORD'.format(host),
         'done']
    )


def make_rpc_script(host, title):
    script_path = '{}/rpc/{}.sh'.format(HOME_DIR, title)
    ensure_dir_of_file(script_path)
    with open(script_path, 'w') as script_file:
        script_file.writelines(rpc_script(host))
    os.system('chmod +x ' + script_path)


def link_smb(host, title):
    source = '/smb/{}'.format(host)
    target = HOME_DIR + '/mnt/' + title
    os.system('rm {}'.format(target))
    os.system('ln -s {} {}'.format(source, target))


def link_ssh(host, user, title):
    source = '/ssh/{}@{}'.format(user, host)
    target = HOME_DIR + '/mnt/' + title
    os.system('rm {}'.format(target))
    os.system('ln -s {} {}'.format(source, target))


def make_ssh_script(host, user, title):
    script_path = '{}/ssh/{}.sh'.format(HOME_DIR, title)
    os.system('rm ' + script_path)
    with open(script_path, 'w') as script_file:
        script_file.writelines([
            '#!/bin/sh\n',
            'ssh {}@{}'.format(user, host)
        ])
    os.system('chmod +x ' + script_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('uri', help='uri of machine to addition')
    parser.add_argument('title', help='title of machine')
    args = parser.parse_args()

    machine = args.uri
    title = args.title

    user, host = parse_uri(machine)
    password = getpass.getpass()

    secret = user + ':' + password
    subprocess.run(
        ['secret-tool', 'store', '--label=' + host, 'target', host, 'created_by', 'add_machine'],
        input=secret, universal_newlines=True)

    if is_port_open(host, SMB):
        print("setting up SMB")
        make_rpc_script(host, title)
        link_smb(host, title)

    if is_port_open(host, RDP):
        print("setting up RDP")
        make_rdp_script(host, title)

    if is_port_open(host, SSH):
        print("setting up SSH")
        os.system('sshpass -p {} ssh-copy-id {}@{}'.format(password, user, host))
        make_ssh_script(host, user, title)
        link_ssh(host, user, title)

main()
