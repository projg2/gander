# (c) 2020 Michał Górny
# 2-clause BSD license

"""Gander CLI"""

import argparse
import json
import os
import re
import secrets
import sys
import typing

from pathlib import Path

import requests

from gander import __version__
from gander.privacy import PRIVACY_POLICY
from gander.report import PortageAPI


DEFAULT_ENDPOINT = 'https://anser.gentoo.org/submit'
DEFAULT_TIMEOUT = 30
MACHINE_ID_RE = re.compile(r'[0-9a-f]{32}')


def make_report(args: argparse.Namespace) -> int:
    api = PortageAPI(config_root=args.config_root)
    data = {
        'goose-version': 1,
        'profile': api.profile,
        'world': api.world,
    }

    try:
        with open(args.machine_id_path, 'r') as f:
            machine_id = f.read().strip()
        if MACHINE_ID_RE.match(machine_id):
            data['id'] = machine_id
        else:
            print(f'Warning: machine-id in {args.machine_id_path} '
                  f'invalid, the report will not be suitable for '
                  f'submission; please run --setup to create a new one',
                  file=sys.stderr)
    except FileNotFoundError:
        print('Warning: no machine-id found, the report will not '
              'be suitable for submission; please run --setup first',
              file=sys.stderr)

    json.dump(data, sys.stdout, indent=2)
    print()
    return 0


def privacy_policy(args: argparse.Namespace) -> int:
    print(PRIVACY_POLICY)
    return 0


def get_default_machine_id_path() -> Path:
    machine_id_path = Path('/etc/gander.id')
    if not os.access(machine_id_path, os.W_OK):
        machine_id_path = (Path(os.environ.get('XDG_CONFIG_HOME',
                                               Path.home() / '.config'))
                           / 'gander.id')
    return machine_id_path


def setup(args: argparse.Namespace) -> int:
    print(PRIVACY_POLICY)
    print()
    while True:
        try:
            resp = input('Do you accept the terms of the Privacy '
                         'Policy? [Y/n] ')
            if not resp or resp.lower() == 'y':
                break
            elif resp.lower() == 'n':
                return 1
            else:
                print('Please answer Y or N.')
        except KeyboardInterrupt:
            print()
            return 1

    # NB: we don't really need cryptographic security but the 'secrets'
    # module is convenient to use
    sysid = secrets.token_hex(16)
    os.makedirs(args.machine_id_path.parent, exist_ok=True)
    with open(args.machine_id_path, 'w') as f:
        f.write(f'{sysid}\n')
    print(f'Machine id: {sysid},\nwritten to {args.machine_id_path}')

    # TODO: set up a cronjob

    return 0


def submit(args: argparse.Namespace) -> int:
    try:
        with open(args.machine_id_path, 'r') as f:
            machine_id = f.read().strip()
        if not MACHINE_ID_RE.match(machine_id):
            raise ValueError(machine_id)
    except (FileNotFoundError, ValueError):
        print('Machine identifier not found or invalid, please run '
              '--setup',
              file=sys.stderr)
        return 1

    api = PortageAPI(config_root=args.config_root)
    data = {
        'goose-version': 1,
        'id': machine_id,
        'profile': api.profile,
        'world': api.world,
    }

    try:
        resp = requests.put(args.api_endpoint,
                            headers={'User-Agent': 'gander'},
                            json=data,
                            timeout=args.timeout)
    except (requests.ConnectionError, requests.Timeout) as e:
        print(f'Report submission failed:\n{e}')
        return 1
    else:
        print(f'The server replied ({resp.status_code}):\n{resp.text}')
        if resp:
            print('It seems that the report has been accepted.')
            return 0
        else:
            print('The submission has failed.')
            if resp.status_code >= 500 and resp.status_code < 600:
                print('The server seems to be having trouble, please '
                      'try again later.')
            elif resp.status_code == 429:
                print('Please wait 7 days between successive '
                      'submissions.')
            elif resp.status_code == 404:
                print('Did you specify a correct API endpoint URL?')
            return 1


def main(argv: typing.List[str]) -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument('--version',
                      action='version',
                      version=f'gander {__version__}',
                      help='print the program version and exit')

    xgroup = (argp.add_argument_group('action')
              .add_mutually_exclusive_group(required=True))
    xgroup.add_argument('--make-report',
                        action='store_const',
                        const=make_report,
                        dest='action',
                        help='create and output system report')
    xgroup.add_argument('--privacy-policy',
                        action='store_const',
                        const=privacy_policy,
                        dest='action',
                        help='print Privacy Policy and exit')
    xgroup.add_argument('--setup',
                        action='store_const',
                        const=setup,
                        dest='action',
                        help='set gander up for submitting reports')
    xgroup.add_argument('--submit',
                        action='store_const',
                        const=submit,
                        dest='action',
                        help='generate and submit report')

    group = argp.add_argument_group('report options')
    group.add_argument('--config-root',
                       type=Path,
                       help='system root path relative to which '
                            'configuration files are loaded')

    group = argp.add_argument_group('submission options')
    machine_id_path = get_default_machine_id_path()
    group.add_argument('--api-endpoint',
                       default=DEFAULT_ENDPOINT,
                       help=f'API endpoint '
                            f'(default: {DEFAULT_ENDPOINT})')
    group.add_argument('--machine-id-path',
                       type=Path,
                       default=machine_id_path,
                       help=f'path to the file containing machine id '
                            f'(default: {machine_id_path})')
    group.add_argument('--timeout',
                       type=int,
                       default=DEFAULT_TIMEOUT,
                       help=f'connection timeout '
                            f'(default: {DEFAULT_TIMEOUT})')

    args = argp.parse_args(argv)
    return args.action(args)


def setuptools_main() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    setuptools_main()
