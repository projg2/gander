# (c) 2020 Michał Górny
# 2-clause BSD license

"""Tests for report generation"""

from pathlib import Path

import os
import os.path
import tempfile
import typing
import unittest

from gander.report import PortageAPI


class PortageAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()

    @staticmethod
    def create_profile_symlink(profpath: Path,
                               etcport: Path
                               ) -> None:
        os.symlink(os.path.relpath(profpath, etcport),
                   etcport / 'make.profile')

    @staticmethod
    def create_profile_abs_symlink(profpath: Path,
                                   etcport: Path
                                   ) -> None:
        os.symlink(profpath,
                   etcport / 'make.profile')

    @staticmethod
    def create_profile_directory(profpath: Path,
                                 etcport: Path
                                 ) -> None:
        etcprof = etcport / 'make.profile'
        os.mkdir(etcprof)
        with open(etcprof / 'parent', 'w') as f:
            f.write(str(profpath))

    @staticmethod
    def create_profile_directory_rel(profpath: Path,
                                     etcport: Path
                                     ) -> None:
        etcprof = etcport / 'make.profile'
        os.mkdir(etcprof)
        with open(etcprof / 'parent', 'w') as f:
            f.write(os.path.relpath(profpath, etcprof))

    @staticmethod
    def create_profile_directory_repo(profpath: Path,
                                      etcport: Path
                                      ) -> None:
        etcprof = etcport / 'make.profile'
        os.mkdir(etcprof)
        with open(etcprof / 'parent', 'w') as f:
            f.write('gentoo:default/linux/amd64')

    @staticmethod
    def create_profile_directory_empty(profpath: Path,
                                      etcport: Path
                                      ) -> None:
        etcprof = etcport / 'make.profile'
        os.mkdir(etcprof)

    @staticmethod
    def create_profile_nongentoo(profpath: Path,
                                 etcport: Path
                                 ) -> None:
        genrepo = etcport.parent.parent / 'gentoo'
        fancyrepo = etcport.parent.parent / 'fancy'
        os.symlink(fancyrepo / profpath.relative_to(genrepo),
                   etcport / 'make.profile')

    def create(self,
               profile_callback: typing.Optional[typing.Callable[
               [Path, Path], None]] = None,
               world: typing.Iterable[str] = []
               ) -> None:
        tempdir = Path(self.tempdir.name)
        etcport = tempdir / 'etc' / 'portage'
        genrepo = tempdir / 'gentoo'
        fancyrepo = tempdir / 'fancy'
        varport = tempdir / 'var' / 'lib' / 'portage'

        # note: order is important since profpath is used below
        for repo, repo_name in ((fancyrepo, 'fancy'),
                                (genrepo, 'gentoo')):
            os.makedirs(repo / 'metadata')
            with open(repo / 'metadata' / 'layout.conf', 'w') as f:
                f.write('masters =')
            profpath = repo / 'profiles' / 'default' / 'linux' / 'amd64'
            os.makedirs(profpath)
            with open(repo / 'profiles' / 'repo_name', 'w') as f:
                f.write(repo_name)
            with open(profpath / 'make.defaults', 'w') as f:
                f.write('''ARCH="amd64"
ACCEPT_KEYWORDS="amd64"
''')

        os.makedirs(etcport / 'sets')
        with open(etcport / 'make.conf', 'w') as f:
            f.write(f'''ROOT={repr(str(tempdir))}
''')
        with open(etcport / 'repos.conf', 'w') as f:
            f.write(f'''[gentoo]
location = {genrepo}

[fancy]
location = {fancyrepo}
''')
        if profile_callback is None:
            profile_callback = self.create_profile_symlink
        profile_callback(profpath, etcport)
        os.makedirs(varport)
        if world:
            with open(varport / 'world', 'w') as f:
                f.write('\n'.join(world))

        self.api = PortageAPI(config_root=self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

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
        self.assertEqual(self.api.world, frozenset(packages))

    def test_world_slotted(self) -> None:
        packages = [
            'dev-libs/foo:3',
            'dev-libs/foo:4/7',
        ]
        self.create(world=packages)
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    def test_world_versioned(self) -> None:
        packages = [
            '<dev-libs/foo-4',
        ]
        self.create(world=packages)
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    def test_world_with_repo(self) -> None:
        packages = [
            'dev-libs/foo::gentoo',
        ]
        self.create(world=packages)
        self.assertEqual(self.api.world, frozenset(('dev-libs/foo',)))

    @unittest.expectedFailure
    def test_world_foreign_package(self) -> None:
        packages = [
            'dev-libs/baz',
        ]
        self.create(world=packages)
        self.assertEqual(self.api.world, frozenset())

    @unittest.expectedFailure
    def test_world_with_foreign_repo(self) -> None:
        packages = [
            'dev-libs/foo::fancy',
        ]
        self.create(world=packages)
        self.assertEqual(self.api.world, frozenset())
