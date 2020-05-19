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

from requests.models import PreparedRequest
import responses

from gander.__main__ import (get_default_machine_id_path,
                             main,
                             MACHINE_ID_RE,
                             )
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
        return patch('gander.__main__.sys.stdin',
                     new_callable=io.StringIO)(subfunc)
    return decorator


class GetDefaultMachineIdPathTests(unittest.TestCase):
    @patch('gander.__main__.os.access')
    def test_root(self,
                  access: MagicMock
                  ) -> None:
        access.return_value = True
        self.assertEqual(
            get_default_machine_id_path(),
            Path('/etc/gander.id'))
        access.assert_called_with(Path('/etc/gander.id'), os.W_OK)

    @patch('gander.__main__.os.environ', new_callable=dict)
    @patch('gander.__main__.os.access')
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

    @patch('gander.__main__.os.environ', new_callable=dict)
    @patch('gander.__main__.os.access')
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
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_privacy_policy(self, sout: io.StringIO) -> None:
        self.assertEqual(
            main(['--privacy-policy']),
            0)
        self.assertIn(PRIVACY_POLICY, sout.getvalue())

    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
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
    expected_report = {
        'goose-version': 1,
        'id': '0123456789abcdef0123456789abcdef',
        'profile': 'default/linux/amd64',
        'world': [
            'dev-libs/bar',
            'dev-libs/foo',
            'dev-util/frobnicate',
        ],
    }

    def setUp(self) -> None:
        super().setUp()
        packages = self.expected_report['world']
        assert isinstance(packages, list)
        self.create(world=packages)
        for x in packages:
            self.create_vdb_package(f'{x}-1')

    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_make_report(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        self.assertEqual(json.loads(sout.getvalue()),
                         self.expected_report)

    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_make_report_invalid_id(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('test\n')

        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        expected = dict(self.expected_report)
        del expected['id']
        self.assertEqual(
            json.loads(sout.getvalue()),
            expected)

    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_make_report_missing_id(self, sout: io.StringIO) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path)]),
            0)
        expected = dict(self.expected_report)
        del expected['id']
        self.assertEqual(
            json.loads(sout.getvalue()),
            expected)

    @responses.activate
    def test_submit_report_missing_id(self) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        self.assertEqual(
            main(['--submit',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            1)

    @responses.activate
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_submit_report(self, sout) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        def handle_request(request: PreparedRequest
                           ) -> typing.Tuple[int,
                                             typing.Dict[str, str],
                                             str]:
            assert request.body is not None
            data = json.loads(request.body)
            self.assertEqual(data, self.expected_report)
            return (200, {}, 'Data added, thanks.')

        responses.add_callback(
            'PUT', 'http://example.com/submit', handle_request)

        self.assertEqual(
            main(['--submit',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            0)
        self.assertNotEqual(sout.getvalue(), '')

    @responses.activate
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_submit_report_quiet(self, sout) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        def handle_request(request: PreparedRequest
                           ) -> typing.Tuple[int,
                                             typing.Dict[str, str],
                                             str]:
            assert request.body is not None
            data = json.loads(request.body)
            self.assertEqual(data, self.expected_report)
            return (200, {}, 'Data added, thanks.')

        responses.add_callback(
            'PUT', 'http://example.com/submit', handle_request)

        self.assertEqual(
            main(['--submit', '--quiet',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            0)
        self.assertEqual(sout.getvalue(), '')

    @responses.activate
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_submit_report_reject_by_limit(self, sout) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        responses.add(
            'PUT',
            'http://example.com/submit',
            status=429,
            body='Rate limit hit')

        self.assertEqual(
            main(['--submit',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            1)
        self.assertNotEqual(sout.getvalue(), '')

    @responses.activate
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_submit_report_reject_by_limit_quiet(self, sout) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        responses.add(
            'PUT',
            'http://example.com/submit',
            status=429,
            body='Rate limit hit')

        self.assertEqual(
            main(['--submit', '--quiet',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            1)
        self.assertNotEqual(sout.getvalue(), '')

    @responses.activate
    @patch('gander.__main__.sys.stdout', new_callable=io.StringIO)
    def test_submit_report_reject_by_limit_no_messages(self,
                                                       sout) -> None:
        machine_id_path = Path(self.tempdir.name) / 'machine-id'
        with open(machine_id_path, 'w') as f:
            f.write('0123456789abcdef0123456789abcdef\n')

        responses.add(
            'PUT',
            'http://example.com/submit',
            status=429,
            body='Rate limit hit')

        self.assertEqual(
            main(['--submit', '--no-messages',
                  '--config-root', self.tempdir.name,
                  '--machine-id-path', str(machine_id_path),
                  '--api-endpoint', 'http://example.com/submit']),
            1)
        self.assertEqual(sout.getvalue(), '')
