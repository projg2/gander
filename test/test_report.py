# (c) 2020 Michał Górny
# 2-clause BSD license

"""Tests for report generation"""

from pathlib import Path

import typing

from gander.report import PortageAPI

from test.repo import EbuildRepositoryTestCase


class PortageAPITests(EbuildRepositoryTestCase):
    def create(self,
               profile_callback: typing.Optional[typing.Callable[
                                 [Path, Path], None]] = None,
               world: typing.Iterable[str] = []
               ) -> None:
        super().create(profile_callback, world)
        self.api = PortageAPI(config_root=Path(self.tempdir.name))

    def test_profile_symlink(self) -> None:
        self.create(profile_callback=self.create_profile_symlink)
        self.assertEqual(self.api.profile, 'default/linux/amd64')

    def test_profile_abs_symlink(self) -> None:
        self.create(profile_callback=self.create_profile_abs_symlink)
        self.assertEqual(self.api.profile, 'default/linux/amd64')

    def test_profile_directory(self) -> None:
        self.create(profile_callback=self.create_profile_directory)
        self.assertEqual(self.api.profile, 'default/linux/amd64')

    def test_profile_directory_rel(self) -> None:
        self.create(profile_callback=self.create_profile_directory_rel)
        self.assertEqual(self.api.profile, 'default/linux/amd64')

    def test_profile_directory_repo(self) -> None:
        self.create(
            profile_callback=self.create_profile_directory_repo)
        self.assertEqual(self.api.profile, 'default/linux/amd64')

    def test_profile_empty(self) -> None:
        self.create(
            profile_callback=self.create_profile_directory_empty)
        self.assertIsNone(self.api.profile)

    def test_profile_nongentoo(self) -> None:
        self.create(
            profile_callback=self.create_profile_nongentoo)
        self.assertIsNone(self.api.profile)

    def test_world_empty(self) -> None:
        self.create()
        self.assertEqual(self.api.world, frozenset())

    def test_world_plain(self) -> None:
        packages = [
            'dev-libs/foo',
            'dev-libs/bar',
            'dev-util/frobnicate'
        ]
        self.create(world=packages)
        for x in packages:
            self.create_vdb_package(f'{x}-1')
        self.assertEqual(self.api.world, frozenset(packages))

    def test_world_slotted(self) -> None:
        packages = [
            'dev-libs/foo:3',
            'dev-libs/foo:4/7',
        ]
        self.create(world=packages)
        self.create_vdb_package('dev-libs/foo-3', SLOT='3')
        self.create_vdb_package('dev-libs/foo-4', SLOT='4/7')
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    def test_world_versioned(self) -> None:
        packages = [
            '<dev-libs/foo-4',
        ]
        self.create(world=packages)
        self.create_vdb_package('dev-libs/foo-3')
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    def test_world_with_repo(self) -> None:
        packages = [
            'dev-libs/foo::gentoo',
        ]
        self.create(world=packages)
        self.create_vdb_package('dev-libs/foo-3')
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    def test_world_foreign_package(self) -> None:
        packages = [
            'dev-libs/baz',
        ]
        self.create(world=packages)
        self.create_vdb_package('dev-libs/baz-3',
                                repository='fancy')
        self.assertEqual(self.api.world, frozenset())

    def test_world_with_foreign_repo(self) -> None:
        """Test when ::gentoo is installed but ::fancy is requested"""
        packages = [
            'dev-libs/foo::fancy',
        ]
        self.create(world=packages)
        self.create_vdb_package('dev-libs/foo-3')
        self.assertEqual(self.api.world, frozenset())
