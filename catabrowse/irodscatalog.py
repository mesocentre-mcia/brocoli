from . import catalog

import re
import os

from six import print_

import irods
from irods.session import iRODSSession
from irods.password_obfuscation import decode
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.collection_manager import CollectionManager
from irods.models import DataObject, Collection
import irods.keywords as kw
import irods.exception as exceptions

def parse_env3(path):
    "parse iRODS v3 iCommands environment files"

    envre = re.compile("^\s*(?P<name>\w+)(\s+|\s*=\s*)[\'\"]?(?P<value1>[^\'\"\n]*)[\'\"]?\s*$")

    ret = {}

    with open(path, 'r') as f:
        for l in f.readlines():
            m = envre.match(l)
            if m:
                ret[m.group("name")] = m.group("value1")

    return ret

def local_tree_stats(dirs):
    total_nfiles = 0
    total_size = 0

    for d in dirs:
        nfiles = 0
        size = 0

        for root, dirs, files in os.walk(d):
            nfiles += len(files)
            size += sum(os.path.getsize(os.path.join(root, name)) for name in files)

        total_nfiles += nfiles
        total_size += size

    return total_nfiles, total_size

def local_files_stats(files):
    return len(files), sum(os.path.getsize(f) for f in files)

class iRODSCatalog(catalog.Catalog):
    def __init__(self, host, port, user, zone, scrambled_password,
                 remove_files_before_overwrite=True):
        self.session = iRODSSession(host=host, port=port, user=user,
                                    password=decode(scrambled_password),
                                    zone=zone)

        self.dom = self.session.data_objects
        self.cm = self.session.collections

        self.remove_files_before_overwrite = remove_files_before_overwrite

    def splitname(self, path):
        return path.rsplit('/', 1)

    def basename(self, path):
        _, basename = self.splitname(path)
        return basename

    def dirname(self, path):
        dirname, _ = self.splitname(path)
        return dirname

    def lstat(self, path):
        if self.isdir(path):
            return self.lstat_dir(path)
        return self.lstat_file(path)

    def lstat_dir(self, path):
        q = self.session.query(Collection.owner_name)
        q = q.filter(Collection.name == path)

        r = q.one()

        ret = {'user': r[Collection.owner_name], 'size': '', 'mtime': ''}

        return ret

    def lstat_file(self, path):
        dirname, basename = self.splitname(path)
        q = self.session.query(DataObject.owner_name, DataObject.size,
                               DataObject.modify_time)
        q = q.filter(Collection.name == dirname)
        q = q.filter(DataObject.name == basename)

        ret = {}
        minsize = None
        maxsize = 0
        for r in q.all():
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

    def listdir(self, path):
        q = self.session.query(DataObject.name).filter(Collection.name == path)
        files = [r[DataObject.name] for r in q.all()]

        q = self.session.query(Collection.name).filter(Collection.parent_name == path)
        colls = [self.basename(c[Collection.name]) for c in q.all()]
        return colls + files

    def isdir(self, path):
        q = self.session.query(Collection.id).filter(Collection.name == path)

        try:
            q.one()
        except irods.exception.NoResultFound:
            return False

        return True

    def join(self, *args):
        return '/'.join(args)

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

    def download_directories(self, pathlist, destdir):
        for p in pathlist:
            coll = self.cm.get(p)
            for y in self._download_coll(coll, destdir):
                yield y

    def upload_files(self, files, path):
        for y in self._upload_files(files, path):
            yield y

    def _upload_files(self, files, path, remove_existing=None):
        if remove_existing is None:
            remove_existing = self.remove_files_before_overwrite
        if not path.endswith('/'):
            path = path + '/'

        options = {kw.FORCE_FLAG_KW: '', kw.ALL_KW: ''}

        number = len(files)
        i = 0
        for f in files:
            basename = os.path.basename(f)
            irods_path = path + basename
            print_('put', f, path, irods_path)

            if remove_existing and self.dom.exists(irods_path):
                # have to remove existing file before writing because force and
                # all flags don't behave as expected (see
                # https://github.com/irods/python-irodsclient/issues/100)
                self.dom.unlink(irods_path, force=True)

            self.dom.put(f, path, **options)

            i += 1
            yield i, number

    def _upload_dir(self, dir_, path):
        files = []
        subdirs = []
        for name in os.listdir(dir_):
            abspath = os.path.join(dir_, name)
            if os.path.isdir(abspath):
                subdirs.append((abspath, name))
            else:
                files.append(abspath)

        for _ in self.upload_files(files, path):
            pass

        for abspath, name in subdirs:
            cpath = self.join(path, name)
            try:
                coll = self.cm.create(cpath)
            except exceptions.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                pass

            self._upload_dir(abspath, cpath)

    def upload_directories(self, dirs, path):
        for d in dirs:
            name = os.path.basename(d)
            cpath = self.join(path, name)

            try:
                self.cm.create(cpath)
            except exceptions.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                pass

            self._upload_dir(d, cpath)

    def delete_files(self, files):
        #q = self.session.query().filter(DataObject.owner_name == 'pigay').count(DataObject.id).sum(DataObject.size).all()
        #print q
        number = len(files)

        i = 0
        for f in files:
            self.dom.unlink(f, force=True)
            i += 1
            yield i, number

    def delete_directories(self, directories):
        number = len(directories)

        i = 0
        for d in directories:
            self.cm.remove(d, recurse=True, force=True)
            i += 1
            yield i, number

    def mkdir(self, path):
        self.cm.create(path)


def make_irods3_catalog(envfile):
    env3 = parse_env3(envfile)

    host = env3['irodsHost']
    port = int(env3.get('irodsPort', '1247'))
    user = env3['irodsUserName']
    zone = env3['irodsZone']
    pwdfile = env3['irodsAuthFileName']

    with open(pwdfile, 'r') as f:
        scrambled_password = f.read().strip()

        return iRODSCatalog(host, port, user, zone, scrambled_password)
