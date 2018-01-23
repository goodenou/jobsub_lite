"""
 Description:
   Query dropbox location to use for an experiment to drop tarballs.  Written
   as a part of the transition to unmount Bluearc from the grid worker nodes.

   # API is /acctgroups/<group>/authmethods/
   API is /acctgroups/<group>/tardirdropboxlocation/
   # API is /acctgroups/<group>/authmethods/<method_name>/

 Project:
   JobSub

 Author:
   Shreyas Bhat

"""
import cherrypy
import logger
import logging
import jobsub
from format import format_response


# @cherrypy.popargs('dropbox_dir')
class TarballDropboxLocationResource(object):
    """see module documentation, only one class in file
    """

    def doGET(self, kwargs):
        """ http GET request on index.html of API
            Query tarball dropbox location. Returns a JSON list object.
            API is /acctgroups/<group>/tardirdropboxlocation/ 
            # API is /acctgroups/<group>/authmethods/
            # API is /acctgroups/<group>/authmethods/<method_name>/
        """
        acctgroup = kwargs.get('acctgroup')
        logger.log('acctgroup=%s' % acctgroup)
        tar_dropbox = jobsub.get_tardir_dropbox(acctgroup)
        if not tar_dropbox:
            cherrypy.response.status = 404
            return {'err': 'Dropbox location for tarball is NOT found for %s'
                % acctgroup}
        return {'out': tar_dropbox}

    @cherrypy.expose
    @format_response
    def index(self, **kwargs):
        """index.html, only GET implemented
        """
        try:
            logger.log("kwargs %s" % kwargs)

            if cherrypy.request.method == 'GET':
                rc = self.doGET(kwargs)
            else:
                err = 'Unsupported method: %s' % cherrypy.request.method
                logger.log(err, severity=logging.ERROR)
                logger.log(err, severity=logging.ERROR, logfile='error')
                rc = {'err': err}
        except:
            err = 'Exception on TarballDropboxLocationResource.index'
            cherrypy.response.status = 500
            logger.log(err, severity=logging.ERROR, traceback=True)
            logger.log(err, severity=logging.ERROR,
                       logfile='error', traceback=True)
            rc = {'err': err}

        return rc
