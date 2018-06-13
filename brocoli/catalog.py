import os
import shutil
from datetime import datetime
from collections import OrderedDict

from six import print_


class Catalog(object):
    """
    Base class for catalog objects. All methods have to be overridden by
    sub-classes.
    """
    def lstat(self, path):
        """
        Returns a dictionary of informations about specified path. Mandatory
        fields are: size, mtime, nreplicas, user, isdir
        """
        raise NotImplementedError

    def listdir(self, path):
        """
        Returns directory contents (only filenames, not absolute paths) in the
        form of a dictionary. Each value of the dictionary has to be itself a
        dictionary as would be returned by lstat()
        """
        raise NotImplementedError

    def isdir(self, path):
        """
        Returns wether the specified path is a directory.
        """
        raise NotImplementedError

    def join(self, *args):
        """
        Performs the equivalent of os.path.join() in the context of the
        Catalog object.
        """
        raise NotImplementedError

    def splitname(self, path):
        """
        Performs the equivalent of os.path.split() in the context of the
        Catalog object.
        """
        raise NotImplementedError

    def dirname(self, path):
        """
        Performs the equivalent of os.path.dirname() in the context of the
        Catalog object.
        """
        raise NotImplementedError

    def basename(self, path):
        """
        Performs the equivalent of os.path.basename() in the context of the
        Catalog object.
        """
        raise NotImplementedError

    def normpath(self, path):
        """
        Performs the equivalent of os.path.normpath() in the context of the
        Catalog object.
        """
        raise NotImplementedError


    def download_files(self, pathlist, destdir, osl):
        """
        Downloads files from the catalog pathlist to local destdir.
        """
        raise NotImplementedError

    def download_directories(self, pathlist, destdir, osl):
        """
        Downloads directories contents to local destdir.
        """
        raise NotImplementedError

    def upload_files(self, files, path, osl):
        """
        Uploads local files to catalog destination path (a directory).
        """
        raise NotImplementedError

    def upload_directories(self, dirs, path, osl):
        """
        Uploads local directories content to catalog destination path (a
        directory).
        """
        raise NotImplementedError

    def delete_files(self, files, osl):
        """
        Deletes catalog files.
        """
        raise NotImplementedError

    def delete_directories(self, directories, osl):
        """
        Recusively deletes catalog directories.
        """
        raise NotImplementedError

    def mkdir(self, path):
        """
        Creates a new catalog directory.
        """
        raise NotImplementedError

    def directory_properties(self, path):
        """
        Returns a dictionary of properties for a directory path
        """
        raise NotImplementedError

    def file_properties(self, path):
        """
        Returns a dictionary of properties for a file path
        """
        raise NotImplementedError

    def close(self):
        pass

    @classmethod
    def config_fields(cls):
        """
        Returns a dictionary of form.FormField objects for catalog object
        configuration.
        """
        raise NotImplementedError


class OperationStatus(object):
    NEW = 0
    IN_PROGRESS = 1
    DONE = 2
    FAILED = 3
    INTERRUPTED = 4

    def __init__(self, size=0, cancel=None):
        self.status = self.NEW
        self.progress = 0
        self.size = size
        self.cancel = cancel or (lambda e: None)

        self.current_element = None

    def in_progress(self, current_element):
        self.status = self.IN_PROGRESS
        self.current_element = current_element

    def done(self):
        self.status = self.DONE
        self.progress = self.size
        self.current_element = None

    def interrupt(self):
        if self.status not in (self.NEW, self.IN_PROGRESS):
            return

        if self.current_element is not None:
            self.cancel(self.current_element)
            self.current_element = None
        self.status = self.INTERRUPTED

    def fail(self):
        self.interrupt()
        self.status = self.FAILED


class OperationStatusList(OrderedDict):
    def __init__(self, keylist=[], cancel=None):
        items = [(k, OperationStatus(cancel=cancel)) for k in keylist]
        super(OperationStatusList, self).__init__(items)

    def finalize(self):
        for os in self.values():
            os.interrupt()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.finalize()

class OSCatalog(Catalog):
    """
    Presents contents from local filesystem. Useful for debugging.
    """
    def lstat(self, path):
        stats = os.lstat(path)

        nreplicas = '1'
        isdir = False
        if self.isdir(path):
            nreplicas = ''
            isdir = True
        ret = {
            'user': stats.st_uid,
            'size': stats.st_size,
            'mtime': datetime.fromtimestamp(stats.st_mtime),
            'nreplicas': nreplicas,
            'isdir': isdir,
        }

        return ret

    def listdir(self, path):
        entries = os.listdir(path)

        directories = []
        files = []

        ret = {}
        for e in entries:
            v = self.lstat(self.join(path, e))
            ret[e] = v

        return ret

    def isdir(self, path):
        return os.path.isdir(path)

    def join(self, *args):
        return os.path.join(*args)

    def splitname(self, path):
        return os.path.split(path)

    def dirname(self, path):
        return os.path.dirname(path)

    def basename(self, path):
        return os.path.basename(path)

    def normpath(self, path):
        return os.path.normpath(path)

    def download_files(self, pathlist, destdir, osl):
        number = len(pathlist)
        for path in pathlist:
            osl[path].size = 1
            osl[path].cancel = os.unlink

        i = 0
        for path in pathlist:
            osl[path].in_progress(os.path.join(destdir, self.basename(path)))
            shutil.copy2(path, destdir)
            osl[path].done()
            i += 1
            yield i, number

    def download_directories(self, pathlist, destdir, osl):
        number = len(pathlist)
        for p in pathlist:
            osl[p].size = 1

        i = 0
        for path in pathlist:
            osl[path].in_progress(None)

            # shutil.copytree needs a fresh new destination directory
            ddir = os.path.join(destdir, os.path.basename(path))
            if os.path.exists(ddir):
                shutil.rmtree(ddir)
            shutil.copytree(path, ddir)

            osl[path].done()

            i += 1
            yield i, number

    def upload_files(self, files, path, osl):
        number = len(files)
        for f in files:
            osl[f].size = 1

        i = 0
        for f in files:
            osl[f].in_progress(None)
            shutil.copy2(f, path)
            osl[f].done()
            i += 1
            yield i, number

    def upload_directories(self, dirs, path, osl):
        number = len(dirs)
        for d in dirs:
            osl[d].size = 1

        i = 0
        for d in dirs:
            osl[d].in_progress(None)

            # shutil.copytree needs a fresh new destination directory
            ddir = os.path.join(path, os.path.basename(d))
            if os.path.exists(ddir):
                shutil.rmtree(ddir)

            shutil.copytree(d, ddir)

            osl[d].done()

            i += 1
            yield i, number

    def delete_files(self, files, osl):
        number = len(files)
        for f in files:
            osl[f].size = 1

        i = 0
        for f in files:
            osl[f].in_progress(None)
            os.unlink(f)
            osl[f].done()
            i += 1
            yield i, number


    def delete_directories(self, directories, osl):
        number = len(directories)
        for d in directories:
            osl[d].size = 1

        i = 0
        for d in directories:
            osl[d].in_progress(None)

            shutil.rmtree(d)

            osl[d].done()

            i += 1
            yield i, number

    def mkdir(self, path):
        os.mkdir(path)

    def directory_properties(self, path):
        return {}

    def file_properties(self, path):
        return {}

    @classmethod
    def config_fields(cls):
        return {}

