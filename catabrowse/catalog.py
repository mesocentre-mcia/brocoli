import os
import shutil
from datetime import datetime

from six import print_

class Catalog(object):
    def lstat(self, path):
        raise NotImplementedError

    def listdir(self, path):
        raise NotImplementedError

    def isdir(self, path):
        raise NotImplementedError

    def join(self, *args):
        raise NotImplementedError

    def download_files(self, pathlist, destdir):
        raise NotImplementedError

    def download_directories(self, pathlist, destdir):
        raise NotImplementedError

    def upload_files(self, files, path):
        raise NotImplementedError

    def upload_directories(self, dirs, path):
        raise NotImplementedError

    def delete_files(self, files):
        raise NotImplementedError

    def delete_directories(self, directories):
        raise NotImplementedError

    def mkdir(self, path):
        raise NotImplementedError

class OSCatalog(Catalog):
    def lstat(self, path):
        stats = os.lstat(path)

        ret = {}

        ret['user'] = stats.st_uid
        ret['size'] = stats.st_size
        ret['mtime'] = datetime.fromtimestamp(stats.st_mtime)

        return ret

    def listdir(self, path):
        return os.listdir(path)

    def isdir(self, path):
        return os.path.isdir(path)

    def join(self, *args):
        return os.path.join(*args)

    def download_files(self, pathlist, destdir):
        for path in pathlist:
            shutil.copy2(path, destdir)

    def download_directories(self, pathlist, destdir):
        for path in pathlist:
            # shutil.copytree needs a fresh new destination directory
            ddir = os.path.join(destdir, os.path.basename(path))
            if os.path.exists(ddir):
                shutil.rmtree(ddir)
            shutil.copytree(path, ddir)

    def upload_files(self, files, path):
        for f in files:
            shutil.copy2(f, path)

    def upload_directories(self, dirs, path):
        for d in dirs:
            # shutil.copytree needs a fresh new destination directory
            ddir = os.path.join(path, os.path.basename(d))
            if os.path.exists(ddir):
                shutil.rmtree(ddir)

            shutil.copytree(d, ddir)

    def delete_files(self, files):
        for f in files:
            os.unlink(f)

    def delete_directories(self, directories):
        for d in directories:
            shutil.rmtree(d)

    def mkdir(self, path):
        os.mkdir(path)
