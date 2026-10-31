import json
import os
import sys


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]


class AttrConfig(dict):
    """
    Simple dict subclass exposing keys as attributes, returning None when the
    requested attribute does not exist.

    This replaces the abandoned 'attrdict' package, which fails to import on
    Python 3.10+ because it uses 'collections.Mapping' instead of
    'collections.abc.Mapping'.
    """

    def __init__(self, config):
        super().__init__(config)
        # Wrap nested containers so attribute access works at any depth
        for key, value in list(self.items()):
            super().__setitem__(key, self._wrap(value))

    @classmethod
    def _wrap(cls, value):
        if isinstance(value, dict):
            return cls(value)
        elif isinstance(value, list):
            # Kept as a list (not a tuple) so config lists stay mutable
            return [cls._wrap(item) for item in value]
        return value

    def __setitem__(self, key, value):
        super().__setitem__(key, self._wrap(value))

    def __getattr__(self, item):
        # Let dunder lookups fail normally, otherwise copy/pickle protocols
        # would receive None instead of raising AttributeError
        if item.startswith('__') and item.endswith('__'):
            raise AttributeError(item)
        # Default behaviour
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value


class Config(object, metaclass=Singleton):
    base_config = {
        'core': {
            'debug': False
        },
        'notifications': {
            'verbose': True
        },
        'automatic': {
            # per-run limits for each list: at most a few titles a day
            'movies': {
                'interval': 24,
                'anticipated': 1,
                'trending': 0,
                'popular': 1,
                'boxoffice': 1
            },
            'shows': {
                'interval': 24,
                'anticipated': 1,
                'trending': 0,
                'popular': 0
            }
        },
        'filters': {
            'shows': {
                'disabled_for': [],
                'allowed_countries': [],
                'allowed_languages': [],
                'blacklisted_genres': [],
                'blacklisted_networks': [],
                'blacklisted_min_runtime': 15,
                'blacklisted_max_runtime': 0,
                'blacklisted_min_year': '{year}',
                'blacklisted_max_year': '{year}+1',
                'blacklisted_title_keywords': [],
                'blacklisted_tvdb_ids': [],
                'allowed_genres': [],
                'released_after': '',
                'released_before': '',
                'anticipated_min_lists': 2500,
            },
            'movies': {
                'disabled_for': [],
                'allowed_countries': [],
                'allowed_languages': [],
                'blacklisted_genres': [],
                'blacklisted_min_runtime': 60,
                'blacklisted_max_runtime': 0,
                'blacklisted_min_year': '{year}',
                'blacklisted_max_year': '{year}+1',
                'blacklisted_title_keywords': [],
                'blacklisted_tmdb_ids': [],
                'rotten_tomatoes': "",
                'allowed_genres': [],
                'released_after': '',
                'released_before': '',
                'anticipated_min_lists': 5000
            }
        },
        'radarr': {
            'api_key': '',
            'minimum_availability': 'released',
            'quality': 'HD-1080p',
            'root_folder': '/movies/',
            'tags': [],
            'url': 'http://localhost:7878/'
        },
        'sonarr': {
            'api_key': '',
            'language': 'Deprecated',     # Sonarr v4+ has no language profiles; v3 needs a profile name
            'quality': 'HD-1080p',
            'root_folder': '/tv/',
            'season_folder': True,
            'tags': [],
            'url': 'http://localhost:8989/'
        },
        'omdb': {
            'api_key': ''
        },
        'trakt': {
            'client_id': '',
            'client_secret': ''
        }
    }

    def __init__(self, configfile, cachefile, logfile):
        """Initializes config"""
        self.conf = None

        self.config_path = configfile
        self.cache_path = cachefile
        self.log_path = logfile

    @property
    def cfg(self):
        # Return existing loaded config
        if self.conf:
            return self.conf

        # Built initial config if it doesn't exist
        if self.build_config():
            print("Please edit the default configuration before running again!")
            sys.exit(0)
        # Load config, upgrade if necessary
        else:
            tmp = self.load_config()
            self.conf, upgraded = self.upgrade_settings(tmp)

            # Save config if upgraded
            if upgraded:
                self.dump_config()
                print("New config options were added, adjust and restart!")
                sys.exit(0)

            return self.conf

    @property
    def cachefile(self):
        return self.cache_path

    @property
    def logfile(self):
        return self.log_path

    def build_config(self):
        if os.path.exists(self.config_path):
            return False
        print("Dumping default config to: %s" % self.config_path)
        with open(self.config_path, 'w') as fp:
            json.dump(self.base_config, fp, sort_keys=True, indent=2)
        return True

    def dump_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'w') as fp:
                json.dump(self.conf, fp, sort_keys=True, indent=2)
            return True
        else:
            return False

    def load_config(self):
        with open(self.config_path, 'r') as fp:
            return AttrConfig(json.load(fp))

    def __inner_upgrade(self, settings1, settings2, key=None, overwrite=False):
        sub_upgraded = False
        merged = settings2.copy()

        if isinstance(settings1, dict):
            for k, v in settings1.items():
                # missing k
                if k not in settings2:
                    merged[k] = v
                    sub_upgraded = True
                    if not key:
                        print("Added %r config option: %s" % (str(k), str(v)))
                    else:
                        print("Added %r to config option %r: %s" % (str(k), str(key), str(v)))
                    continue

                # iterate children
                if isinstance(v, (dict, list)):
                    merged[k], did_upgrade = self.__inner_upgrade(settings1[k], settings2[k], key=k,
                                                                  overwrite=overwrite)
                    sub_upgraded = did_upgrade or sub_upgraded
                elif settings1[k] != settings2[k] and overwrite:
                    merged = settings1
                    sub_upgraded = True
        elif isinstance(settings1, list) and key:
            for v in settings1:
                if v not in settings2:
                    merged.append(v)
                    sub_upgraded = True
                    print("Added to config option %r: %s" % (str(key), str(v)))
                    continue

        return merged, sub_upgraded

    def upgrade_settings(self, currents):
        upgraded_settings, upgraded = self.__inner_upgrade(self.base_config, currents)
        return AttrConfig(upgraded_settings), upgraded

    def merge_settings(self, settings_to_merge):
        upgraded_settings, upgraded = self.__inner_upgrade(settings_to_merge, self.conf, overwrite=True)

        self.conf = upgraded_settings

        if upgraded:
            self.dump_config()

        return AttrConfig(upgraded_settings), upgraded
