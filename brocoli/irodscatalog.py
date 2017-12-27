"""
Implements iRODS Catalog object and methods
"""

from . import catalog
from . import form
from . import exceptions
from . listmanager import ColumnDef, List

import re
import os
import hashlib
import collections

from six import print_
from six.moves import tkinter as tk

import irods
from irods.session import iRODSSession
from irods import password_obfuscation
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.collection_manager import CollectionManager
from irods.models import DataObject, Collection
import irods.keywords as kw
import irods.exception

_getuid = None
if hasattr(os, 'getuid'):
    _getuid = os.getuid
else:
    # generate a fake uid on systems that lacks os.getuid()
    _getuid = lambda: int('0x' + hashlib.md5(os.getlogin().encode()).hexdigest(), 16) % 10000


def parse_env3(path):
    """
    parse iRODS v3 iCommands environment files
    """

    pat = ("^\s*(?P<name>\w+)" + "(\s+|\s*=\s*)[\'\"]?(?P<value1>[^\'\"\n]*)" +
           "[\'\"]?\s*$")
    envre = re.compile(pat)

    ret = {}

    with open(path, 'r') as f:
        for l in f.readlines():
            m = envre.match(l)
            if m:
                ret[m.group("name")] = m.group("value1")

    return ret


def local_tree_stats(dirs):
    """
    Gathers stats (number of files and cumulated size) of sub-trees on a local
    directories list
    """
    total_nfiles = 0
    total_size = 0

    for d in dirs:
        nfiles = 0
        size = 0

        for root, dirs, files in os.walk(d):
            nfiles += len(files)
            size += sum(os.path.getsize(os.path.join(root, name))
                        for name in files)

        total_nfiles += nfiles
        total_size += size

    return total_nfiles, total_size


def local_files_stats(files):
    """
    Computes stats (number of files and cumulated size) on a file list
    """
    return len(files), sum(os.path.getsize(f) for f in files)


def translate_exceptions(method):
    """
    Method decorator that translates iRODS to Brocoli exceptions
    """
    def method_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            raise exceptions.ConnectionError(e)
        except irods.exception.CAT_UNKNOWN_COLLECTION as e:
            raise exceptions.FileNotFoundError(e)

    return method_wrapper


class iRODSCatalog(catalog.Catalog):
    """
    A Catalog for connectiong to iRODS
    """
    @classmethod
    def encode(cls, s):
        return password_obfuscation.encode(s, _getuid())

    @classmethod
    def decode(cls, s):
        return password_obfuscation.decode(s, _getuid())

    def __init__(self, host, port, user, zone, scrambled_password):
        try:
            password = iRODSCatalog.decode(scrambled_password)
            self.session = iRODSSession(host=host, port=port, user=user,
                                        password=password, zone=zone)
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            raise exceptions.ConnectionError(e)

        self.dom = self.session.data_objects
        self.cm = self.session.collections

    def splitname(self, path):
        return path.rsplit('/', 1)

    def basename(self, path):
        _, basename = self.splitname(path)
        return basename

    def dirname(self, path):
        dirname, _ = self.splitname(path)
        return dirname

    @translate_exceptions
    def lstat(self, path):
        if self.isdir(path):
            return self.lstat_dir(path)
        return self.lstat_file(path)

    def lstat_dir(self, path):
        q = self.session.query(Collection.owner_name)
        q = q.filter(Collection.name == path)

        r = q.one()

        ret = {
            'user': r[Collection.owner_name],
            'size': '',
            'mtime': '',
            'nreplicas': '',
        }

        return ret

    def lstat_file(self, path):
        dirname, basename = self.splitname(path)
        q = self.session.query(DataObject.owner_name, DataObject.size,
                               DataObject.modify_time)
        q = q.filter(Collection.name == dirname)
        q = q.filter(DataObject.name == basename)

        replicas = q.all()
        if len(replicas) < 1:
            # no replica
            raise exceptions.ioerror(exceptions.errno.ENOENT)

        ret = {'nreplicas': len(replicas)}
        minsize = None
        maxsize = 0
        for r in replicas:
            ret['user'] = r[DataObject.owner_name]
            ret['mtime'] = r[DataObject.modify_time]
            size = r[DataObject.size]
            if minsize is None or size < minsize:
                minsize = size
            if size > maxsize:
                maxsize = size

        if maxsize != minsize:
            ret['size'] = '{}-{}'.format(minsize, maxsize)
        else:
            ret['size'] = str(minsize)

        return ret

    @translate_exceptions
    def listdir(self, path):
        q = self.session.query(DataObject.name).filter(Collection.name == path)
        files = [r[DataObject.name] for r in q.all()]

        q = self.session.query(Collection.name) \
            .filter(Collection.parent_name == path)
        colls = [self.basename(c[Collection.name]) for c in q.all()]
        return colls + files

    @translate_exceptions
    def isdir(self, path):
        q = self.session.query(Collection.id).filter(Collection.name == path)

        try:
            q.one()
        except irods.exception.NoResultFound:
            return False

        return True

    def join(self, *args):
        return '/'.join(args)

    @translate_exceptions
    def download_files(self, pathlist, destdir):
        options = {kw.FORCE_FLAG_KW: ''}

        number = len(pathlist)
        i = 0
        for p in pathlist:
            self.dom._download(p, destdir, **options)
            i += 1
            yield i, number

    def _download_coll(self, coll, destdir):
        destdir = os.path.join(destdir, coll.name)
        try:
            os.makedirs(destdir)
        except OSError:
            if not os.path.isdir(destdir):
                raise

        pathlist = [dobj.path for dobj in list(coll.data_objects)]
        for y in self.download_files(pathlist, destdir):
            yield y

        for subcoll in coll.subcollections:
            for y in self._download_coll(subcoll, destdir):
                yield y

    @translate_exceptions
    def download_directories(self, pathlist, destdir):
        for p in pathlist:
            coll = self.cm.get(p)
            for y in self._download_coll(coll, destdir):
                yield y

    @translate_exceptions
    def upload_files(self, files, path):
        nfiles, size = local_files_stats(files)

        completed = 0
        for s in self._upload_files(files, path):
            completed += s
            yield completed, size

    def _upload_files(self, files, path):
        def local_file_md5(filename):
            m = hashlib.md5()
            with open(filename, 'rb') as f:
                m.update(f.read())

            return m.hexdigest()

        if not path.endswith('/'):
            path = path + '/'

        options = {
            kw.VERIFY_CHKSUM_KW: '',
            kw.ALL_KW: '',
            kw.UPDATE_REPL_KW: '',
        }

        for f in files:
            basename = os.path.basename(f)
            irods_path = path + basename
            print_('put', f, path, irods_path)

            options[kw.VERIFY_CHKSUM_KW] = local_file_md5(f)

            self.dom.put(f, irods_path, **options)

            yield os.path.getsize(f)

    def _upload_dir(self, dir_, path):
        files = []
        subdirs = []
        for name in os.listdir(dir_):
            abspath = os.path.join(dir_, name)
            if os.path.isdir(abspath):
                subdirs.append((abspath, name))
            else:
                files.append(abspath)

        for y in self._upload_files(files, path):
            yield y

        for abspath, name in subdirs:
            cpath = self.join(path, name)
            try:
                coll = self.cm.create(cpath)
                remove = False
            except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                pass

            for y in self._upload_dir(abspath, cpath):
                yield y

    @translate_exceptions
    def upload_directories(self, dirs, path):
        nfiles, size = local_tree_stats(dirs)

        completed = 0
        for d in dirs:
            name = os.path.basename(d)
            cpath = self.join(path, name)

            try:
                self.cm.create(cpath)
            except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                pass

            for s in self._upload_dir(d, cpath):
                completed += s
                yield completed, size

    @translate_exceptions
    def delete_files(self, files):
        number = len(files)

        i = 0
        for f in files:
            self.dom.unlink(f, force=True)
            i += 1
            yield i, number

    @translate_exceptions
    def delete_directories(self, directories):
        number = len(directories)

        i = 0
        for d in directories:
            self.cm.remove(d, recurse=True, force=True)
            i += 1
            yield i, number

    @translate_exceptions
    def mkdir(self, path):
        self.cm.create(path)

    @translate_exceptions
    def path_properties(self, path):
        if self.isdir(path):
            return {}

        do = self.dom.get(path)
        replicas = [r.__dict__.copy() for r in do.replicas]
        for r in replicas:
            # set row title for ListManager use
            r['#0'] = r['number']
        replicas_list = List(iRODSCatalog.replicas_def(), replicas)

        return collections.OrderedDict([
            ('Replicas', replicas_list),
        ])

    @classmethod
    def replicas_def(cls):
        repl_num = ColumnDef('#0', 'number',
                             form_field=form.IntegerField('Replica number:', -1))
        resc = ColumnDef('resource_name', 'Resource',
                         form_field=form.TextField('Resource name:'))

        path = ColumnDef('path', 'Path',
                         form_field=form.TextField('Replica path:'))

        status = ColumnDef('status', 'Status',
                           form_field=form.TextField('Replica status:'))

        checksum = ColumnDef('checksum', 'Checksum',
                           form_field=form.TextField('Replica checksum:'))

        cols = [repl_num, resc, status, checksum, path]

        return collections.OrderedDict([(cd.name, cd) for cd in cols])

    @classmethod
    def config_fields(cls):

        tags = ['inline_config']

        return collections.OrderedDict([
            ('use_irods_env', form.BooleanField('Use irods environment file',
                                                disables_tags=tags)),
            ('host', form.HostnameField('iRODS host:', tags=tags)),
            ('port', form.IntegerField('iRODS port:', '1247', tags=tags)),
            ('zone', form.TextField('iRODS zone:', tags=tags)),
            ('user_name', form.TextField('iRODS user name:', tags=tags)),
            ('store_password', form.BooleanField('Remember password',
                                                 enables_tags=['password'],
                                                 tags=tags)),
            ('password', form.PasswordField('iRODS password:',
                                            encode=cls.encode,
                                            decode=cls.decode,
                                            tags=tags + ['password'])),
        ])


def irods3_catalog_from_envfile(envfile):
    """
    Creates an iRODSCatalog from a iRODS v3 configuration file (like
    "~/.irods/.irodsEnv")
    """
    env3 = parse_env3(envfile)

    host = env3['irodsHost']
    port = int(env3.get('irodsPort', '1247'))
    user = env3['irodsUserName']
    zone = env3['irodsZone']
    pwdfile = env3['irodsAuthFileName']

    with open(pwdfile, 'r') as f:
        scrambled_password = f.read().strip()

    return iRODSCatalog(host, port, user, zone, scrambled_password)


def irods3_catalog_from_config(cfg):
    """
    Creates an iRODSCatalog from configuration
    """
    use_env = False
    if cfg['use_irods_env'].lower() in ['1', 'yes', 'on', 'true']:
        use_env = True
    elif cfg['use_irods_env'].lower() in ['0', 'no', 'off', 'false']:
        use_env = False
    else:
        msg = 'invalid irods_use_env value: {}'.format(cfg['use_irods_env'])
        raise ValueError(msg)

    if use_env:
        envfile = os.path.join(os.path.expanduser('~'), '.irods', '.irodsEnv')
        return lambda master: irods3_catalog_from_envfile(envfile)

    host = cfg['host']
    port = cfg['port']
    user = cfg['user_name']
    zone = cfg['zone']
    store_password = cfg['store_password']
    scrambled_password = None
    if store_password.lower() in ['1', 'yes', 'on', 'true']:
        scrambled_password = cfg['password']
        return lambda master: iRODSCatalog(host, port, user, zone,
                                           scrambled_password)
    else:
        def ask_password(master):
            tl = tk.Toplevel(master)
            tl.transient(master)

            ff = form.FormFrame(tl)
            pf = form.PasswordField('enter iRODS password:',
                                    return_cb=tl.destroy)
            ff.grid_fields([pf])
            ff.pack()

            tl.wait_window()

            scrambled_password = iRODSCatalog.encode(pf.to_string())

            return iRODSCatalog(host, port, user, zone, scrambled_password)

        return ask_password
