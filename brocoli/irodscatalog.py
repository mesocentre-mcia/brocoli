"""
Implements iRODS Catalog object and methods
"""

from . import catalog
from . import form
from . import exceptions
from . listmanager import ColumnDef, List
from . config_option import option_is_true

from . irodsdom import ModifiedDataObjectManager

import re
import os
import io
import hashlib
import base64
import collections
import datetime
import ssl
from datetime import timezone

from six import print_
from six.moves import tkinter as tk

import irods
from irods.session import iRODSSession
from irods import password_obfuscation
from irods.manager.data_object_manager import DataObjectManager
from irods.manager.collection_manager import CollectionManager
from irods.models import DataObject, Collection
from irods.manager import data_object_manager
from irods.data_object import chunks
from irods.column import Like
from irods.api_number import api_number
import irods.keywords as kw
import irods.constants as const
import irods.message as message
import irods.exception

_getuid = None
if hasattr(os, 'getuid'):
    _getuid = os.getuid
else:
    import getpass

    # generate a fake uid on systems that lacks os.getuid()
    def _fake_getuid():
        return int('0x' + hashlib.md5(getpass.getuser().encode()).hexdigest(),
                   16) % 10000

    _getuid = _fake_getuid


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


def local_trees_stats(dirs):
    """
    Gathers stats (number of files and cumulated size) of sub-trees on a local
    directories list
    """
    total_nfiles = 0
    total_size = 0
    stats = {}

    for d in dirs:
        nfiles = 0
        size = 0

        for root, dirs, files in os.walk(d):
            nfiles += len(files)
            size += sum(os.path.getsize(os.path.join(root, name))
                        for name in files)
        stats[d] = size

        total_nfiles += nfiles
        total_size += size

    return total_nfiles, total_size, stats


def local_files_stats(files):
    """
    Computes stats (number of files and cumulated size) on a file list
    """
    stats = {f: os.path.getsize(f) for f in files}
    return len(files), sum(v for v in stats.values()), stats


def method_translate_exceptions(method):
    """
    Method decorator that translates iRODS to Brocoli exceptions
    """
    def method_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            self.close()
            raise exceptions.ConnectionError(e)
        except (irods.exception.NetworkException, ssl.SSLError) as e:
            raise exceptions.NetworkError(e)
        except irods.exception.CAT_UNKNOWN_COLLECTION as e:
            raise exceptions.FileNotFoundError(e)
        except irods.exception.CAT_SQL_ERR as e:
            raise exceptions.CatalogLogicError(e)

    return method_wrapper


def function_translate_exceptions(func):
    """
    Function decorator that translates iRODS to Brocoli exceptions
    """
    def function_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            raise exceptions.ConnectionError(e)
        except irods.exception.NetworkException as e:
            raise exceptions.NetworkError(e)
        except irods.exception.CAT_UNKNOWN_COLLECTION as e:
            raise exceptions.FileNotFoundError(e)
        except irods.exception.CAT_SQL_ERR as e:
            raise exceptions.CatalogLogicError(e)

    return function_wrapper


class iRODSCatalogBase(catalog.Catalog):
    """
    A base class Catalog for connecting to iRODS
    """

    BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE * 1000

    def local_file_cksum(self, filename, algorithm=None):
        def get_digest(h):
            if h.name == 'sha256':
                return 'sha2:' + base64.b64encode(h.digest()).decode()

            return h.hexdigest()

        if algorithm is None:
            algorithm = getattr(self.session.pool.account,
                                'default_hash_scheme', 'SHA256').lower()

        scheme = hashlib.new(algorithm)
        with open(filename, 'rb') as f:
            for chunk in chunks(f, self.BUFFER_SIZE):
                scheme.update(chunk)
                yield len(chunk), ''

        yield 0, get_digest(scheme)

    def local_file_cksum_ref(self, filename, ref_cksum):
        algorithm = None
        if ref_cksum.startswith('sha2:'):
            algorithm = 'sha256'

        for y in self.local_file_cksum(filename, algorithm):
            yield y

    @classmethod
    def encode(cls, s):
        return password_obfuscation.encode(s, _getuid())

    @classmethod
    def decode(cls, s):
        return password_obfuscation.decode(s, _getuid())

    def __init__(self, session, default_resc, local_checksum):
        self.session = session

        self.default_resc = default_resc

        self.local_checksum = local_checksum

        self.dom = ModifiedDataObjectManager(self.session)
        self.cm = self.session.collections
        try:
            self.am = self.session.acls
        except AttributeError:
            # prc < 2.0.0
            self.am = self.session.permissions

    def close(self):
        self.session.cleanup()

    def cksum_factor(self):
        return 2 if self.local_checksum else 1

    def splitname(self, path):
        return path.rsplit('/', 1)

    def basename(self, path):
        _, basename = self.splitname(path)
        return basename

    def dirname(self, path):
        dirname, _ = self.splitname(path)
        return dirname

    def normpath(self, path):
        pathlist = []

        for t in path.split('/'):
            if t == '' or t == '.':
                continue

            if t == '..':
                if len(pathlist):
                    del pathlist[-1]
                continue

            pathlist.append(t)

        normpath = '/'.join([''] + pathlist)

        return normpath or '/'

    @method_translate_exceptions
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
            'isdir': True,
        }

        return ret

    def lstat_dirs(self, parent_path):
        q = self.session.query(Collection.name, Collection.owner_name)
        q = q.filter(Collection.parent_name == parent_path)

        ret = {}
        for r in q.get_results():

            ret[self.basename(r[Collection.name])] = {
                'user': r[Collection.owner_name],
                'size': '',
                'mtime': '',
                'nreplicas': '',
                'isdir': True,
            }

        return ret

    def lstat_files(self, dirname):
        epoch = datetime.datetime(1, 1, 1)

        q = self.session.query(DataObject.name, DataObject.owner_name,
                               DataObject.size,
                               DataObject.modify_time,
                               DataObject.replica_number)
        q = q.filter(Collection.name == dirname)

        ret = {}
        for r in q.get_results():
            name = r[DataObject.name]
            dobj = ret.get(name, {'minsize': None, 'maxsize': 0,
                                  'mtime': epoch, 'isdir': False,
                                  'nreplicas': 0})

            dobj['user'] = r[DataObject.owner_name]
            dobj['nreplicas'] += 1

            dobj['mtime'] = r[DataObject.modify_time]

            size = r[DataObject.size]
            if dobj['minsize'] is None or size < dobj['minsize']:
                dobj['minsize'] = size

            if size > dobj['maxsize']:
                dobj['maxsize'] = size

            ret[name] = dobj

        for k, v in ret.items():
            minsize = v['minsize']
            maxsize = v['maxsize']
            if maxsize != minsize:
                v['size'] = '{}-{}'.format(minsize, maxsize)
            else:
                v['size'] = str(minsize)

        return ret

    def lstat_file(self, path):
        dirname, basename = self.splitname(path)
        q = self.session.query(DataObject.owner_name, DataObject.size,
                               DataObject.modify_time,
                               DataObject.replica_number)
        q = q.filter(Collection.name == dirname)
        q = q.filter(DataObject.name == basename)

        replicas = q.all()
        if len(replicas) < 1:
            # no replica
            raise exceptions.ioerror(exceptions.errno.ENOENT)

        ret = {'nreplicas': len(replicas), 'isdir': False}
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

    @method_translate_exceptions
    def listdir(self, path):
        q = self.session.query(DataObject.name).filter(Collection.name == path)
        files = [r[DataObject.name] for r in q.all()]

        q = self.session.query(Collection.name) \
            .filter(Collection.parent_name == path)
        colls = [self.basename(c[Collection.name]) for c in q.all()]

        ret = self.lstat_dirs(path)
        ret.update(self.lstat_files(path))

        return ret

    @method_translate_exceptions
    def isdir(self, path):
        q = self.session.query(Collection.id).filter(Collection.name == path)

        try:
            q.one()
        except irods.exception.NoResultFound:
            return False

        return True

    def join(self, *args):
        return '/'.join(args)

    def remote_files_stats(self, file_paths):
        dirs = {self.dirname(p) for p in file_paths}

        stats = {}
        for d in dirs:
            q = self.session.query(DataObject.name, DataObject.size)
            q = q.filter(Collection.name == d)

            for r in q.get_results():
                stats[self.join(d, r[DataObject.name])] = \
                  int(r[DataObject.size])

        return (len(file_paths),
                sum([v for k, v in stats.items() if k in file_paths]),
                stats)

    def remote_trees_stats(self, dirs):
        nfiles = 0
        size = 0
        stats = {}

        for d in dirs:
            # need to keep column 'collection_id' to avoid 'distinct' clause on
            # recursive queries
            q = self.session.query(DataObject.collection_id, DataObject.name,
                                   DataObject.size)

            dsize = 0
            # first level query
            q1 = q.filter(Collection.name == d)
            for r in q1.get_results():
                nfiles += 1
                dsize += int(r[DataObject.size])

            # recursive query
            qr = q.filter(Like(Collection.name, self.join(d, '%')))
            for r in qr.get_results():
                nfiles += 1
                dsize += int(r[DataObject.size])

            stats[d] = dsize
            size += dsize

        return nfiles, size, stats

    @method_translate_exceptions
    def download_files(self, pathlist, destdir, osl):
        nfiles, size, stats = self.remote_files_stats(pathlist)

        def cancel(f):
            print_('interrupted: delete', f)
            os.unlink(f)

        cksum_factor = self.cksum_factor()
        size *= cksum_factor
        stats = {k : (s * cksum_factor) for k, s in stats.items()}
        osl.update_list(pathlist, size=stats, cancel=cancel)

        if nfiles > 1 or size > self.BUFFER_SIZE:
            # wake up progress bar for more than one file or one large file
            yield 0, size

        completed = 0
        for y in self._download_files(pathlist, destdir, osl):
            completed += y
            yield completed, size

    def _download_files(self, pathlist, destdir, osl, status_path=None):
        def _download(obj, file, **options):
            # adapted from https://github.com/irods/python-irodsclient
            # data_object_manager.py#L29

            # Check for force flag if file exists
            if os.path.exists(file) and kw.FORCE_FLAG_KW not in options:
                raise ex.OVERWRITE_WITHOUT_FORCE_FLAG

            with open(file, 'wb') as f, self.dom.open(obj, 'r', **options) as o:
                for chunk in chunks(o, self.BUFFER_SIZE):
                    f.write(chunk)
                    yield len(chunk)

            obj_cksum = self.dom.get(obj).checksum
            if self.local_checksum:
                obj_cksum = self.dom.get(obj).checksum
                if obj_cksum is not None:
                    local_cksum = None
                    for l, local_cksum in self.local_file_cksum_ref(file,
                                                                    obj_cksum):

                        yield l

                    if local_cksum != obj_cksum:
                        # FIXME: delete local file?
                        msg = 'Downloaded file has an incorrect checksum ' \
                              '(local=\'{}\', ' \
                              'catalog=\'{}\')'.format(local_cksum, obj_cksum)
                        raise exceptions.ChecksumError(msg)
                    else:
                        print_('checksum ok', local_cksum)
                else:
                    print_('checksum is None')

        options = {kw.FORCE_FLAG_KW: ''}

        for p in pathlist:
            print_('get', p, destdir)

            destfile = os.path.join(destdir, self.basename(p))
            sp = status_path or p
            osl[sp].in_progress(destfile)
            for y in _download(p, destfile, **options):
                osl[sp].progress += y
                yield y

            if sp == p:
                osl[p].done()

    def _download_coll(self, coll, destdir, osl, status_path):
        destdir = os.path.join(destdir, coll.name)
        try:
            os.makedirs(destdir)
        except OSError:
            if not os.path.isdir(destdir):
                raise

        query = self.session.query(DataObject.name)\
            .filter(Collection.name == coll.path)

        results = query.get_results()

        pathlist = [self.join(coll.path, r[DataObject.name]) for r in results]
        for y in self._download_files(pathlist, destdir, osl, status_path):
            yield y

        for subcoll in coll.subcollections:
            for y in self._download_coll(subcoll, destdir, osl, status_path):
                yield y

    @method_translate_exceptions
    def download_directories(self, pathlist, destdir, osl):
        nfiles, size, stats = self.remote_trees_stats(pathlist)

        def cancel(f):
            print_('interrupted: delete', f)
            os.unlink(f)

        cksum_factor = self.cksum_factor()
        size *= cksum_factor
        stats = {k : (s * cksum_factor) for k, s in stats.items()}
        osl.update_list(pathlist, size=stats, cancel=cancel)

        completed = 0
        for p in pathlist:
            coll = self.cm.get(p)
            osl[p].in_progress(None)
            for y in self._download_coll(coll, destdir, osl, p):
                completed += y
                yield completed, size

            osl[p].done()

    @method_translate_exceptions
    def upload_files(self, files, path, osl):
        nfiles, size, stats = local_files_stats(files)

        def cancel(f):
            print_('interrupted: delete', f)
            self.dom.unlink(f, force=True)

        cksum_factor = self.cksum_factor()
        size *= cksum_factor
        stats = {k : (s * cksum_factor) for k, s in stats.items()}
        osl.update_list(files, size=stats, cancel=cancel)

        completed = 0
        for s in self._upload_files(files, path, osl):
            completed += s
            yield completed, size

    def _upload_files(self, files, path, osl, status_path=None):
        def _put(file, obj, **options):
            # adapted from https://github.com/irods/python-irodsclient
            # data_object_manager.py#L60

            # Set operation type to trigger acPostProcForPut
            if kw.OPR_TYPE_KW not in options:
                options[kw.OPR_TYPE_KW] = 1  # PUT_OPR

            with open(file, 'rb') as f:
                closed = False
                o = self.dom.open(obj, 'w', **options)

                try:
                    for chunk in chunks(f, self.BUFFER_SIZE):
                        o.write(chunk)
                        yield len(chunk)
                except GeneratorExit:
                    # generator was interrupted

                    closed = True
                    try:
                        o.close()
                    except irods.exception.USER_CHKSUM_MISMATCH:
                        # it's normal that cksum fails since we were interrupted
                        # -> ignore
                        pass
                    return

                finally:
                    # close data object except already done
                    if not closed:
                        o.close()

#            if kw.ALL_KW in options:
#                options[kw.UPDATE_REPL_KW] = ''
#                self.dom.replicate(obj, **options)

        if not path.endswith('/'):
            path = path + '/'

        options = {
            kw.ALL_KW: '',
            kw.UPDATE_REPL_KW: '',
        }

        if self.default_resc is not None:
            options[kw.DEST_RESC_NAME_KW] = self.default_resc

        for f in files:
            basename = os.path.basename(f)
            irods_path = path + basename
            print_('put', f, path, irods_path)

            if os.stat(f).st_size > self.BUFFER_SIZE:
                # wake up progress bar before checksum for large files
                yield 0

            sp = status_path or f
            osl[sp].in_progress(irods_path)

            if self.local_checksum:
                cksum = None
                for l, cksum in self.local_file_cksum(f):
                    osl[sp].progress += l
                    yield l
                options[kw.VERIFY_CHKSUM_KW] = cksum
                print_('cksum', options[kw.VERIFY_CHKSUM_KW])

            try:
                for y in _put(f, irods_path, **options):
                    osl[sp].progress += y
                    yield y
            except irods.exception.USER_CHKSUM_MISMATCH as e:
                # remove object from catalog?
                # self.dom.unlink(irods_path, force=True)

                # mark failed and reraise
                os[sp].fail()

                raise exceptions.CatalogLogicError(e)

            if sp == f:
                osl[f].done()

    def _upload_dir(self, dir_, path, osl, status_path=None):
        files = []
        subdirs = []

        try:
            self.cm.create(path)
        except irods.exception.CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
            pass

        for name in os.listdir(dir_):
            abspath = os.path.join(dir_, name)
            if os.path.isdir(abspath):
                subdirs.append((abspath, name))
            else:
                files.append(abspath)

        for y in self._upload_files(files, path, osl, status_path):
            yield y

        for abspath, name in subdirs:
            cpath = self.join(path, name)

            for y in self._upload_dir(abspath, cpath, osl, status_path):
                yield y

    @method_translate_exceptions
    def upload_directories(self, dirs, path, osl):
        nfiles, size, stats = local_trees_stats(dirs)

        def cancel(f):
            print_('interrupted: delete', f)
            self.dom.unlink(f, force=True)

        cksum_factor = self.cksum_factor()
        size *= cksum_factor
        stats = {k : (s * cksum_factor) for k, s in stats.items()}
        osl.update_list(dirs, size=stats, cancel=cancel)

        completed = 0
        for d in dirs:
            name = os.path.basename(d)
            cpath = self.join(path, name)

            osl[d].in_progress(None)
            for s in self._upload_dir(d, cpath, osl, d):
                completed += s
                yield completed, size

            osl[d].done()

    @method_translate_exceptions
    def delete_files(self, files, osl):
        number = len(files)

        i = 0
        for f in files:
            osl[f].size = 1
            osl[f].in_progress(None)
            self.dom.unlink(f, force=True)
            osl[f].done()
            i += 1
            yield i, number

    def _coll_remove_yield(self, path, recurse=True, force=False, **options):
        """
        interruptible version of CollectionManager.coll_remove() method
        """
        if recurse:
            options[kw.RECURSIVE_OPR__KW] = ''
        if force:
            options[kw.FORCE_FLAG_KW] = ''

        try:
            oprType = options[kw.OPR_TYPE_KW]
        except KeyError:
            oprType = 0

        message_body = message.CollectionRequest(
            collName=path,
            flags=0,
            oprType=oprType,
            KeyValPair_PI=message.StringStringMap(options)
        )
        msg = message.iRODSMessage('RODS_API_REQ', msg=message_body,
                                   int_info=api_number['RM_COLL_AN'])
        with self.session.pool.get_connection() as conn:
            conn.send(msg)
            response = conn.recv()

            try:
                while response.int_info == const.SYS_SVR_TO_CLI_COLL_STAT:
                    conn.reply(const.SYS_CLI_TO_SVR_COLL_STAT_REPLY)
                    yield
                    response = conn.recv()
            except GeneratorExit:
                # destroy connection which is in a bad state (could fix?)
                conn.release(destroy=True)

    @method_translate_exceptions
    def delete_directories(self, directories, osl):
        number = len(directories)

        i = 0
        for d in directories:
            osl[d].size = 1
            osl[d].in_progress(None)
            for y in self._coll_remove_yield(d, recurse=True, force=True):
                yield i, number
            osl[d].done()
            i += 1
            yield i, number

    @method_translate_exceptions
    def mkdir(self, path):
        self.cm.create(path)

    def __acls_from_object(self, obj):
        access = self.am.get(obj)

        acls = [a.__dict__.copy() for a in access]

        for a in acls:
            # build a unique ttk.TreeWidget iid
            a['iid'] = '#'.join([a[t] for t in ['user_name', 'user_zone',
                                                'access_name']])
            a['#0'] = a['user_name']

        @function_translate_exceptions
        def add(result):
            access_name = result['access_name']
            user_name = result['#0']
            user_zone = result['user_zone']

            acl = irods.access.iRODSAccess(access_name, obj.path, user_name,
                                           user_zone)

            self.session.permissions.set(acl)

            return '#'.join([user_name, user_zone, access_name])

        @function_translate_exceptions
        def remove(result):
            user_name = result['#0']
            user_zone = result['user_zone']

            acl = irods.access.iRODSAccess('null', obj.path, user_name,
                                           user_zone)

            self.session.permissions.set(acl)

        acls_def = iRODSCatalogBase.acls_def(self.session.zone)

        return List(acls_def, acls, add_cb=add, remove_cb=remove)

    def __metadata_from_object(self, obj):
        metadata = [md.__dict__.copy() for md in obj.metadata.items()]

        for md in metadata:
            md['iid'] = md['avu_id']
            md['#0'] = md['name']

        @function_translate_exceptions
        def add(result):
            name = result['#0']
            value = result['value']
            units = result['units']

            obj.metadata.add(name, value, units)

            for md in obj.metadata.items():
                if md.name == name and md.value and md.units == units:
                    return md.avu_id

            return None

        @function_translate_exceptions
        def remove(result):
            name = result['#0']
            value = result['value']
            unit = result['units']

            obj.metadata.remove(name, value, unit)

        return List(iRODSCatalogBase.metadata_def(), metadata, add_cb=add,
                    remove_cb=remove)

    @method_translate_exceptions
    def directory_properties(self, path):
        co = self.cm.get(path)
        acls_list = self.__acls_from_object(co)
        metadata_list = self.__metadata_from_object(co)

        inheritance = self.session.query(Collection.inheritance) \
            .filter(Collection.name == path).one()[Collection.inheritance] \
            == '1'

        def inheritance_changed(value):
            name = 'inherit' if value else 'noinherit'
            acl = irods.access.iRODSAccess(name, path, '', '')

            self.session.permissions.set(acl)

        f = form.BooleanField('Inherit:', inheritance,
                              state_change_cb=inheritance_changed)
        inherit_frame = form.FrameGenerator([f])

        return collections.OrderedDict([
            ('Permissions', acls_list),
            ('Metadata', metadata_list),
            ('Inheritance', inherit_frame),
        ])

    @method_translate_exceptions
    def file_properties(self, path):
        do = self.dom.get(path)
        replicas = [r.__dict__.copy() for r in do.replicas]
        for r in replicas:
            # set row title for ListManager use
            r['#0'] = r['number']

        replicas_list = List(iRODSCatalogBase.replicas_def(), replicas)

        acls_list = self.__acls_from_object(do)
        metadata_list = self.__metadata_from_object(do)

        return collections.OrderedDict([
            ('Replicas', replicas_list),
            ('Permissions', acls_list),
            ('Metadata', metadata_list),
        ])

    @classmethod
    def replicas_def(cls):
        repl_num = ColumnDef('#0', 'Number',
                             form_field=form.IntegerField('Replica number:',
                                                          -1))
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
    def acls_def(cls, default_zone=''):
        user = ColumnDef('#0', 'User', form_field=form.TextField('User:'))
        zone = ColumnDef('user_zone', 'Zone',
                         form_field=form.TextField('User zone:', default_zone))
        access_types = ['read', 'write', 'own']
        type = ColumnDef('access_name', 'Access type',
                         form_field=form.ComboboxChoiceField('Acces type:',
                                                             access_types,
                                                             access_types[0]))

        cols = [user, zone, type]

        return collections.OrderedDict([(cd.name, cd) for cd in cols])

    @classmethod
    def metadata_def(cls):
        name = ColumnDef('#0', 'Name',
                         form_field=form.TextField('Metadata name:'))
        value = ColumnDef('value', 'Value',
                          form_field=form.TextField('Metadata value:'))
        unit = ColumnDef('units', 'Unit',
                         form_field=form.TextField('Metadata unit:'))

        cols = [name, value, unit]

        return collections.OrderedDict([(cd.name, cd) for cd in cols])

    @classmethod
    def config_fields(cls):

        tags = ['inline_config']

        return collections.OrderedDict([
            ('local_checksum', form.BooleanField('Perform local checksum:',
                                                 default_value=True)),
            ('use_irods_env', form.BooleanField('Use irods environment file:',
                                                disables_tags=tags)),
            ('host', form.HostnameField('iRODS host:', tags=tags)),
            ('port', form.IntegerField('iRODS port:', '1247', tags=tags)),
            ('zone', form.TextField('iRODS zone:', tags=tags)),
            ('user_name', form.TextField('iRODS user name:', tags=tags)),
            ('default_resc', form.TextField('Default resource:', tags=tags)),
            ('store_password', form.BooleanField('Remember password:',
                                                 enables_tags=['password'],
                                                 tags=tags)),
            ('password', form.PasswordField('iRODS password:',
                                            encode=cls.encode,
                                            decode=cls.decode,
                                            tags=tags + ['password'])),
        ])


class iRODSCatalog3(iRODSCatalogBase):
    """
    A Catalog for connecting to iRODS v3
    """

    def __init__(self, host, port, user, zone, scrambled_password,
                 default_resc, local_checksum):
        try:
            password = iRODSCatalogBase.decode(scrambled_password)
            session = iRODSSession(host=host, port=port, user=user,
                                   password=password, zone=zone,
                                   default_hash_scheme='MD5')
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            raise exceptions.ConnectionError(e)

        super(iRODSCatalog3, self).__init__(session, default_resc,
                                            local_checksum)


class iRODSCatalog4(iRODSCatalogBase):
    """
    A Catalog for connecting to iRODS v4
    """

    @classmethod
    def from_env_file(cls, env_file, local_checksum):
        session = iRODSSession(irods_env_file=env_file)

        return cls(session, None, local_checksum)

    @classmethod
    def from_options(cls, host, port, user, zone, scrambled_password,
                     default_resc, local_checksum, default_hash_scheme,
                     authentication_scheme, ssl_settings=None):
        kwargs = {}
        try:
            password = iRODSCatalogBase.decode(scrambled_password)
            kwargs.update(dict(host=host, port=port, user=user,
                               password=password, zone=zone,
                               default_hash_scheme=default_hash_scheme,
                               authentication_scheme=authentication_scheme))
        except irods.exception.CAT_INVALID_AUTHENTICATION as e:
            raise exceptions.ConnectionError(e)

        if ssl_settings is not None:
            kwargs.update(ssl_settings)

        session = iRODSSession(**kwargs)

        return cls(session, default_resc, local_checksum)

    @classmethod
    def config_fields(cls):
        base_dict = iRODSCatalogBase.config_fields()

        tags = base_dict['host'].tags

        base_dict.update({
            ('irods_authentication_scheme',
             form.RadioChoiceField('Authentication scheme',
                                   values=['native', 'pam'],
                                   default_value='native',
                                   tags=tags)),
            ('irods_default_hash_scheme',
             form.RadioChoiceField('Default hash scheme',
                                   values=['MD5', 'SHA256'],
                                   default_value='SHA256',
                                   tags=tags)),
        })

        ssl_tag = 'ssl_config'

        ssl_tags = tags + [ssl_tag]

        ssl_options = collections.OrderedDict([
            ('irods_client_server_policy',
             form.RadioChoiceField('irods_client_server_policy',
                                   values=['CS_NEG_REQUIRE', 'CS_NEG_REFUSE',
                                           'CS_NEG_DONT_CARE'],
                                   default_value='CS_NEG_REQUIRE',
                                   tags=tags)),

            ('use_irods_ssl', form.BooleanField('Use irods SSL transfer',
                                                enables_tags=[ssl_tag],
                                                tags=tags)),
            ('irods_encryption_algorithm',
             form.TextField('irods_encryption_algorithm:',
                            default_value='AES-256-CBC', tags=ssl_tags)),
            ('irods_encryption_key_size',
             form.IntegerField('irods_encryption_key_size:', default_value='32',
                               tags=ssl_tags)),
            ('irods_encryption_num_hash_rounds',
             form.IntegerField('irods_encryption_num_hash_rounds:',
                               default_value='16', tags=ssl_tags)),
            ('irods_encryption_salt_size',
             form.IntegerField('irods_encryption_salt_size:', default_value='8',
                               tags=ssl_tags)),
            ('irods_ssl_ca_certificate_file',
             form.FileSelectorField('irods_ssl_ca_certificate_file:',
                                    tags=ssl_tags)),
        ])

        base_dict.update(ssl_options)

        return base_dict


def irods3_catalog_from_envfile(envfile, local_checksum):
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
    default_resc = env3.get('irodsDefResource', None)

    with open(pwdfile, 'r') as f:
        scrambled_password = f.read().strip()

    return iRODSCatalog3(host, port, user, zone, scrambled_password,
                         default_resc, local_checksum)


def irods3_catalog_from_config(cfg):
    """
    Creates an iRODSCatalog from configuration
    """
    local_checksum = option_is_true(cfg.get('local_checksum', 'True'))
    use_env = option_is_true(cfg['use_irods_env'])

    if use_env:
        envfile = os.path.join(os.path.expanduser('~'), '.irods', '.irodsEnv')
        return lambda master: irods3_catalog_from_envfile(envfile,
                                                          local_checksum)

    host = cfg['host']
    port = cfg['port']
    user = cfg['user_name']
    zone = cfg['zone']

    default_resc = cfg.get('default_resc', None)
    if default_resc == '':
        # empty string is not valid for default_resc
        default_resc = None

    store_password = cfg['store_password']
    scrambled_password = None
    if option_is_true(store_password):
        scrambled_password = cfg['password']
        return lambda master: iRODSCatalog3(host, port, user, zone,
                                            scrambled_password, default_resc,
                                            local_checksum)
    else:
        def ask_password(master):
            cancelled = {'cancelled': False}

            def _do_ok(e=None):
                tl.destroy()

            def _do_cancel(e=None):
                pf.from_string('')
                cancelled['cancelled'] = True
                tl.destroy()

            tl = tk.Toplevel(master)
            tl.title('iRODS password')
            tl.transient(master)

            ff = form.FormFrame(tl)
            pf = form.PasswordField('password for {}@{}:'.format(user, zone),
                                    return_cb=_do_ok)
            ff.grid_fields([pf])
            ff.pack()

            butbox = tk.Frame(tl)
            butbox.pack()
            ok = tk.Button(butbox, text='Ok', command=_do_ok)
            ok.grid()
            ok.bind('<Return>', _do_ok)
            cancel = tk.Button(butbox, text='Cancel', command=_do_cancel)
            cancel.grid(row=0, column=1)
            cancel.bind('<Return>', _do_cancel)

            tl.wait_window()

            if cancelled['cancelled']:
                return None

            scrambled_password = iRODSCatalogBase.encode(pf.to_string())

            return iRODSCatalog3(host, port, user, zone, scrambled_password,
                                 default_resc, local_checksum)

        return ask_password


def irods4_catalog_from_config(cfg):
    """
    Creates an iRODSCatalog from configuration
    """
    local_checksum = option_is_true(cfg.get('local_checksum', 'True'))
    use_env = option_is_true(cfg['use_irods_env'])

    if use_env:
        envfile = os.path.join(os.path.expanduser('~'), '.irods',
                               'irods_environment.json')
        return lambda master: iRODSCatalog4.from_env_file(envfile,
                                                          local_checksum)

    host = cfg['host']
    port = cfg['port']
    user = cfg['user_name']
    zone = cfg['zone']

    default_hash_scheme = cfg['irods_default_hash_scheme']
    authentication_scheme = cfg.get('irods_authentication_scheme', 'native')

    ssl = None
    if option_is_true(cfg['use_irods_ssl']):
        ssl = {
            'irods_client_server_negotiation': 'request_server_negotiation',
            'irods_client_server_policy': cfg['irods_client_server_policy'],
            'irods_encryption_algorithm': cfg['irods_encryption_algorithm'],
            'irods_encryption_key_size': int(cfg['irods_encryption_key_size']),
            'irods_encryption_num_hash_rounds':
                int(cfg['irods_encryption_num_hash_rounds']),
            'irods_encryption_salt_size':
                int(cfg['irods_encryption_salt_size']),
            'irods_ssl_ca_certificate_file':
                cfg['irods_ssl_ca_certificate_file'],
        }

    default_resc = cfg.get('default_resc', None)
    if default_resc == '':
        # empty string is not valid for default_resc
        default_resc = None

    store_password = cfg['store_password']
    scrambled_password = None
    if option_is_true(store_password):
        scrambled_password = cfg['password']
        return lambda master: iRODSCatalog4.from_options(host, port, user,
                                                         zone,
                                                         scrambled_password,
                                                         default_resc,
                                                         local_checksum,
                                                         default_hash_scheme,
                                                         authentication_scheme,
                                                         ssl)
    else:
        def ask_password(master):
            cancelled = {'cancelled': False}

            def _do_ok(e=None):
                tl.destroy()

            def _do_cancel(e=None):
                pf.from_string('')
                cancelled['cancelled'] = True
                tl.destroy()

            tl = tk.Toplevel(master)
            tl.title('iRODS password')
            tl.transient(master)

            ff = form.FormFrame(tl)
            pf = form.PasswordField('password for {}@{}:'.format(user, zone),
                                    return_cb=_do_ok)
            ff.grid_fields([pf])
            ff.pack()

            butbox = tk.Frame(tl)
            butbox.pack()
            ok = tk.Button(butbox, text='Ok', command=_do_ok)
            ok.grid()
            ok.bind('<Return>', _do_ok)
            cancel = tk.Button(butbox, text='Cancel', command=_do_cancel)
            cancel.grid(row=0, column=1)
            cancel.bind('<Return>', _do_cancel)

            tl.wait_window()

            if cancelled['cancelled']:
                return None

            scrambled_password = iRODSCatalogBase.encode(pf.to_string())

            return iRODSCatalog4.from_options(host, port, user, zone,
                                              scrambled_password, default_resc,
                                              local_checksum,
                                              default_hash_scheme,
                                              authentication_scheme, ssl)

        return ask_password
