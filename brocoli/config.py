from . import catalog
from . import irodscatalog

from six.moves import configparser

import os
import os.path
import stat
import tempfile
import collections

default_config_filename = os.path.expanduser('~/.brocoli.ini')

catalog_dict = {
    'os': catalog.OSCatalog,
    'irods3': irodscatalog.iRODSCatalog,
}

catalog_types = list(catalog_dict.keys())


class Config(collections.OrderedDict):

    def connection(self, name=None):
        name = name or self['SETTINGS']['default_connection']

        conn = self['connection:' + name]

        cat = None
        catalog_type = conn['catalog_type']
        if catalog_type == 'os':
            cat = catalog.OSCatalog()
        elif catalog_type == 'irods3':
            cat = irodscatalog.irods3_catalog_from_config(conn)

        return cat, conn['root_path']

    def connection_names(self):
        return [k.split(':', 1)[1] for k in self if k.startswith('connection:')]


def load_config(filename=None):
    filename = filename or default_config_filename

    config = configparser.RawConfigParser()

    if os.path.exists(filename):
        config.read(filename)
    else:
        config['SETTINGS'] = {
            'default_connection': 'default',
        }
        config['connection:default'] = {
            'catalog_type': 'os',
            'root_path': tempfile.mkdtemp(),
        }

    ret = Config()

    for section in config.sections():
        ret[section] = collections.OrderedDict(config.items(section))

    return ret

def save_config(config_dict, filename=None, update=False):
    filename = filename or default_config_filename

    config = configparser.RawConfigParser()

    if update and os.path.exists(filename):
        config.read(filename)

    for section, section_content in config_dict.items():
        if not config.has_section(section):
            config.add_section(section)

        for option, option_value in section_content.items():
            config.set(section, option, option_value)

    with open(filename, 'wt') as f:
        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR)
        config.write(f)
