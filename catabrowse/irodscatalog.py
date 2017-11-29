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


class iRODSCatalog(catalog.Catalog):
    def __init__(self, host, port, user, zone, scrambled_password):
        self.session = iRODSSession(host=host, port=port, user=user,
                                    password=decode(scrambled_password),
                                    zone=zone)

        self.dom = DataObjectManager(self.session)
        self.cm = CollectionManager(self.session)

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
        for p in pathlist:
            self.dom._download(p, destdir, options={'forceFlag': True})

    def _download_coll(self, coll, destdir):
        destdir = os.path.join(destdir, coll.name)
        try:
            os.makedirs(destdir)
        except OSError as e:
            if not os.path.isdir(destdir):
                raise e

        # FIXME: dobj.path not ok (is physical path on resource)
        self.download_files([dobj.path for dobj in list(coll.data_objects)], destdir)

        for subcoll in coll.subcollections:
            self._download_coll(subcoll, destdir)

    def download_directories(self, pathlist, destdir):
        for p in pathlist:
            coll = self.cm.get(p)
            self._download_coll(coll, destdir)

    def upload_files(self, files, path):
        if not path.endswith('/'):
            path = path + '/'
        for f in files:
            self.dom.put(f, path, options={kw.FORCE_FLAG_KW: '',
                                           kw.ALL_KW: ''})

    def _upload_dir(self, dir_, path):
        files = []
        subdirs = []
        for name in os.listdir(dir_):
            abspath = os.path.join(dir_, name)
            if os.path.isdir(abspath):
                subdirs.append((abspath, name))
            else:
                files.append(abspath)

        self.upload_files(files, path)

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
        for f in files:
            self.dom.unlink(f, force=True)

    def delete_directories(self, directories):
        for d in directories:
            self.cm.remove(d, recurse=True, force=True)

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
