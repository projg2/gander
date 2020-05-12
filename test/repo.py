# (c) 2020 Michał Górny
# 2-clause BSD license

"""Test ebuild repository generator"""

import os
import os.path
import tempfile
import typing
import unittest

from pathlib import Path


class EbuildRepositoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

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

    def create_vdb_package(self,
                           pkg: str,
                           **kwargs: str
                           ) -> None:
        vdir = Path(self.tempdir.name) / 'var' / 'db' / 'pkg' / pkg
        os.makedirs(vdir)
        kwargs.setdefault('repository', 'gentoo')
        for k, v in kwargs.items():
            with open(vdir / k, 'w') as f:
                f.write(v)
