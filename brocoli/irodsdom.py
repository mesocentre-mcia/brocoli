from irods.manager.data_object_manager import DataObjectManager

from irods.models import DataObject
import irods.exception as ex
import irods.keywords as kw
from irods.data_object import iRODSDataObject, irods_dirname, irods_basename

class ModifiedDataObjectManager(DataObjectManager):
    def get(self, path, file=None, **options):
        parent = self.sess.collections.get(irods_dirname(path))

        # TODO: optimize
        if file:
            self._download(path, file, **options)

        query = self.sess.query(DataObject)\
            .filter(DataObject.name == irods_basename(path))\
            .filter(DataObject.collection_id == parent.id)\
            .add_keyword(kw.ZONE_KW, path.split('/')[1])

        results = query.all() # get up to max_rows replicas
        if len(results) <= 0:
            raise ex.DataObjectDoesNotExist()
        # workaround incompatibility of irodsclient-0.8.2 and iRODS server 3.x
        for r in results:
            if DataObject.resc_hier not in r:
                r[DataObject.resc_hier] = None
        return iRODSDataObject(self, parent, results)


