
from six.moves import configparser

import os
import os.path
import stat
import tempfile
import collections

default_config_filename = os.path.expanduser('~/.catabrowse.ini')

def load_config(filename=None):
    filename = filename or default_config_filename

    config = configparser.SafeConfigParser()

    if os.path.exists(filename):
        config.read(filename)
    else:
        config['SETTINGS'] = {
            'default_connection': 'connection:default',
        }
        config['connection:default'] = {
            'catalog_type': 'os',
            'root_path': tempfile.mkdtemp(),
        }

    ret = {}

    for section in config.sections():
        ret[section] = collections.OrderedDict(config.items(section))

    return ret

def save_config(config_dict, filename=None, update=False):
    filename = filename or default_config_filename

    config = configparser.SafeConfigParser()

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
