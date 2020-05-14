# (c) 2020 Michał Górny
# 2-clause BSD license

"""Tests for CLI"""

import io
import json
import unittest

from unittest.mock import patch

from gander.cli import main
from gander.privacy import PRIVACY_POLICY

from test.repo import EbuildRepositoryTestCase


class CLIBareTests(unittest.TestCase):
    @patch('gander.cli.sys.stdout', new_callable=io.StringIO)
    def test_make_report(self, sout: io.StringIO) -> None:
        self.assertEqual(
            main(['--privacy-policy']),
            0)
        self.assertIn(PRIVACY_POLICY, sout.getvalue())


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
        self.assertEqual(
            main(['--make-report',
                  '--config-root', self.tempdir.name]),
            0)
        self.assertEqual(
            json.loads(sout.getvalue()),
            {
                'goose-version': 1,
                'profile': 'default/linux/amd64',
                'world': sorted(self.packages),
            })
