# (c) 2020 Michał Górny
# 2-clause BSD license

"""Report generation routines"""

from pathlib import Path

import typing

from portage import create_trees
from portage._sets import load_default_config


class GentooRepoNotFound(Exception):
    """::gentoo repository has not been found on system"""

    pass


class PortageAPI(object):
    """Portage API wrapper"""

    def __init__(self,
                 config_root: typing.Optional[Path] = None
                 ) -> None:
        """
        Instantiate a new instance and load Portage configs

        Load Portage config from optional `config_root`.  If it is not
        specified, the current Portage configuration is loaded.
        """

        kwargs = {}
        if config_root is not None:
            kwargs['config_root'] = config_root
        trees = create_trees(**kwargs)
        self.tree = trees[max(trees)]
        self.dbapi = self.tree['porttree'].dbapi
        self.vdb = self.tree['vartree']

        for r in self.dbapi.repositories:
            if r.name == 'gentoo':
                self.repo = r
                break
        else:
            raise GentooRepoNotFound(
                'Unable to find ::gentoo repository')

    @property
    def profile(self) -> typing.Optional[str]:
        """
        Currently selected profile

        Get the currently selected profile.  Supports both direct
        profile choice via a symlink, and make.profile directory
        with a parent entry.  Return None if the profile can't
        be established or if it is a non-Gentoo profile.
        """

        profiledir = Path(self.repo.location) / 'profiles'
        for p in reversed(self.tree['porttree'].settings.profiles):
            # skip /etc entries
            if p in (self.dbapi.settings.user_profile_dir,
                     self.dbapi.settings.profile_path):
                continue
            # TODO: what about non-Gentoo profiles that reference
            # Gentoo profiles?
            try:
                return str(Path(p).relative_to(profiledir))
            except ValueError:
                break
        return None

    @property
    def world(self) -> typing.Set[str]:
        """
        Packages currently enabled via @world set

        Get the set of packages listed in the @world set.  The atoms
        present in the result are returned as plain package names.
        Return an empty list if there is no @world set.
        """

        setconf = load_default_config(self.dbapi.settings, self.tree)
        ret = set()
        for x in setconf.getSetAtoms('world'):
            m = self.vdb.dep_bestmatch(x)
            if not m:
                # skip uninstalled packages
                continue
            repo, = self.vdb.dbapi.aux_get(m, ['repository'])
            if repo and repo != 'gentoo':
                # skip packages from other repositories
                continue
            ret.add(x.cp)
        return ret
