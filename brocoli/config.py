from . import catalog
from . import irodscatalog

from six.moves import configparser

import os
import os.path
import stat
import tempfile
import collections

# default config location
default_config_filename = os.path.join(os.path.expanduser('~'),
                                       '.brocoli.ini')

# available catalogs
catalog_dict = {
    'os': catalog.OSCatalog,
    'irods3': irodscatalog.iRODSCatalog,
}

catalog_types = list(catalog_dict.keys())

SETTINGS = 'SETTINGS'


class Config(collections.OrderedDict):
    """
    Holds the brocoli configuration loaded from the config file
    """

    def connection(self, name=None):
        name = name or self.default_connection_name()

        conn = self['connection:' + name]

        cat = None
        catalog_type = conn['catalog_type']
        if catalog_type == 'os':
            cat = lambda master: catalog.OSCatalog()
        elif catalog_type == 'irods3':
            cat = irodscatalog.irods3_catalog_from_config(conn)

        return cat, conn['root_path']

    def connection_names(self):
        return [k.split(':', 1)[1] for k in self if k.startswith('connection:')]

    def default_connection_name(self):
        return self[SETTINGS]['default_connection']


def bootstrap_config_parser(config):
    """
    Fills ConfigParser object with minimal values
    """
    config.add_section(SETTINGS)
    config.set(SETTINGS, 'default_connection', 'default')
    config.add_section('connection:default')
    config.set('connection:default', 'catalog_type', 'os')
    config.set('connection:default', 'root_path', tempfile.gettempdir())


def load_config(filename=None):
    """
    Loads configuration from file
    """
    filename = filename or default_config_filename

    config = configparser.RawConfigParser()

    if os.path.exists(filename):
        config.read(filename)
    else:
        bootstrap_config_parser(config)

    ret = Config()

    for section in config.sections():
        ret[section] = collections.OrderedDict(config.items(section))

    return ret


def save_config(config_dict, filename=None, update=False):
    """
    Writes configuration to a file
    """
    filename = filename or default_config_filename

    config = configparser.RawConfigParser()

    if update:
        if os.path.exists(filename):
            config.read(filename)
        else:
            bootstrap_config_parser(config)

    for section, section_content in config_dict.items():
        if not config.has_section(section):
            config.add_section(section)

        for option, option_value in section_content.items():
            config.set(section, option, option_value)

    with open(filename, 'wt') as f:
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        config.write(f)
