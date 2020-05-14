# (c) 2020 Michał Górny
# 2-clause BSD license

"""Tests for CLI"""

import io
import json
import os
import tempfile
import typing
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from gander.cli import get_default_machine_id_path, main, MACHINE_ID_RE
from gander.privacy import PRIVACY_POLICY

from test.repo import EbuildRepositoryTestCase


def patch_stdin(data: str
                ) -> typing.Callable[[typing.Callable], typing.Callable]:
    def decorator(func: typing.Callable) -> typing.Callable:
        def subfunc(self: object,
                    sin: io.StringIO,
                    *args: typing.Any,
                    **kwargs: typing.Any
                    ) -> typing.Any:
            sin.write(data)
            sin.seek(0)
            return func(self, *args, **kwargs)
        return patch('gander.cli.sys.stdin',
                     new_callable=io.StringIO)(subfunc)
    return decorator


class GetDefaultMachineIdPathTests(unittest.TestCase):
    @patch('gander.cli.os.access')
    def test_root(self,
                  access: MagicMock
                  ) -> None:
        access.return_value = True
        self.assertEqual(
            get_default_machine_id_path(),
            Path('/etc/gander.id'))
        access.assert_called_with(Path('/etc/gander.id'), os.W_OK)

    @patch('gander.cli.os.environ', new_callable=dict)
    @patch('gander.cli.os.access')
    def test_xdg_config_home(self,
                             access: MagicMock,
                             environ: dict
                             ) -> None:
        access.return_value = False
        environ['XDG_CONFIG_HOME'] = '/foo'
        self.assertEqual(
            get_default_machine_id_path(),
            Path('/foo/gander.id'))
        access.assert_called_with(Path('/etc/gander.id'), os.W_OK)

    @patch('gander.cli.os.environ', new_callable=dict)
    @patch('gander.cli.os.access')
    def test_default_config(self,
                            access: MagicMock,
                            environ: dict
                            ) -> None:
        access.return_value = False
        environ['HOME'] = '/foo'
        self.assertEqual(
            get_default_machine_id_path(),
            Path('/foo/.config/gander.id'))
        access.assert_called_with(Path('/etc/gander.id'), os.W_OK)


class CLIBareTests(unittest.TestCase):
    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def test_privacy_policy(self, sout: io.StringIO) -> None:
        self.assertEqual(
            main(['--privacy-policy']),
            0)
        self.assertIn(PRIVACY_POLICY, sout.getvalue())

    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def assert_setup(self,
                     sout: io.StringIO,
                     exit_status: int = 0
                     ) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            machine_id_path = Path(tempdir) / 'subdir' / 'machine-id'
            self.assertEqual(
                main(['--setup',
                      '--machine-id-path', str(machine_id_path)]),
                exit_status)
            if exit_status == 0:
                with open(machine_id_path) as f:
                    self.assertRegex(f.read().strip(), MACHINE_ID_RE)
            else:
                self.assertFalse(machine_id_path.exists())

        self.assertIn(PRIVACY_POLICY, sout.getvalue())

    @patch_stdin('\n')
    def test_setup_enter(self) -> None:
        self.assert_setup()

    @patch_stdin('y\n')
    def test_setup_y(self) -> None:
        self.assert_setup()

    @patch_stdin('n\n')
    def test_setup_n(self) -> None:
        self.assert_setup(exit_status=1)


class CLIRepoTests(EbuildRepositoryTestCase):
    def setUp(self) -> None:
        super().setUp()
        packages = [
            'dev-libs/foo',
            'dev-libs/bar',
            'dev-util/frobnicate'
        ]
        self.create(world=packages)
        for x in packages:
            self.create_vdb_package(f'{x}-1')
        self.packages = sorted(packages)

    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def test_make_report(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        self.assertEqual(
            json.loads(sout.getvalue()),
            {
                'goose-version': 1,
                'id': '0123456789abcdef0123456789abcdef',
                'profile': 'default/linux/amd64',
                'world': sorted(self.packages),
            })

    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def test_make_report_invalid_id(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('test\n')

        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        self.assertEqual(
            json.loads(sout.getvalue()),
            {
                'goose-version': 1,
                'profile': 'default/linux/amd64',
                'world': sorted(self.packages),
            })

    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def test_make_report_missing_id(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        self.assertEqual(
            json.loads(sout.getvalue()),
            {
                'goose-version': 1,
                'profile': 'default/linux/amd64',
                'world': sorted(self.packages),
            })
