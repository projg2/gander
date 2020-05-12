# (c) 2020 Michał Górny
# 2-clause BSD license

"""Gander CLI"""

import argparse
import json
import sys
import typing

from pathlib import Path

from gander import __version__
from gander.report import PortageAPI


def make_report(args: argparse.Namespace) -> int:
    api = PortageAPI(config_root=args.config_root)
    data = {
        'goose-version': 1,
        'profile': api.profile,
        'world': api.world,
    }
    # TODO: system id

    json.dump(data, sys.stdout, indent=2)
    print()
    return 0


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

    group = argp.add_argument_group('report options')
    group.add_argument('--config-root',
                       type=Path,
                       help='system root path relative to which '
                            'configuration files are loaded')

    args = argp.parse_args(argv)
    return args.action(args)


def setuptools_main() -> None:
    sys.exit(main(sys.argv[1:]))


if __name__ == '__main__':
    setuptools_main()
