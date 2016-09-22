"""
Module: queued_jobs
Purpose: performs condor_q for jobsub server
Author: Nick
"""
import cherrypy
import logger
import logging

from request_headers import get_client_dn
from format import format_response
from condor_commands import ui_condor_q, constructFilter
from history import HistoryResource
from summary import JobSummaryResource
from jobid import QueuedJobsByJobIDResource
from queued_outformat import QueuedFormattedOutputResource
from queued_jobstatus import QueuedJobStatusResource
#from queued_constraint import QueuedConstraintResource


#@cherrypy.popargs('acctgroup')
@cherrypy.popargs('user_id')
@cherrypy.popargs('job_id')
class QueuedJobsResource(object):
    """ Query list of user_ids. Returns a JSON list object.
    API is /acctgroups/<group>/users/<uid>/jobs
     """

    def __init__(self):
        """constructor
        """
        self.history = HistoryResource()
        self.summary = JobSummaryResource()
        self.jobid = QueuedJobsByJobIDResource()
        qfo = QueuedFormattedOutputResource()
        self.long = qfo
        self.dags = qfo
        qjs = QueuedJobStatusResource()
        self.hold = qjs
        self.run = qjs
        self.idle = qjs
        #self.constraint = QueuedConstraintResource()

    def doGET(self, user_id, job_id=None, kwargs=None):
        """perform http GET
        """
        # acctgroup=kwargs.get('acctgroup')
        # job_id=kwargs.get('job_id')
        if user_id is None and kwargs is not None:
            user_id = kwargs.get('user_id')
        my_filter = constructFilter(None, user_id, job_id)
        logger.log("my_filter=%s" % my_filter)
        history = ui_condor_q(my_filter)
        return {'out': history.split('\n')}

    @cherrypy.expose
    @format_response(output_format='pre')
    def index(self, user_id=None, job_id=None, **kwargs):
        """index.html for
            /acctgroups/<group>/users/<uid>/jobs
        """
        try:
            subject_dn = get_client_dn()
            logger.log("user_id %s" % user_id)
            logger.log("job_id %s" % job_id)
            logger.log("kwargs %s" % kwargs)
            if subject_dn is not None:

                logger.log('subject_dn: %s' % subject_dn)
                if cherrypy.request.method == 'GET':
                    r_code = self.doGET(user_id, job_id, kwargs)
                else:
                    err = 'Unsupported method: %s' % cherrypy.request.method
                    logger.log(err, severity=logging.ERROR)
                    logger.log(err, severity=logging.ERROR, logfile='error')
                    r_code = {'err': err}
            else:
                # return error for no subject_dn
                err = 'User has not supplied subject dn'
                logger.log(err, severity=logging.ERROR)
                logger.log(err, severity=logging.ERROR, logfile='error')
                r_code = {'err': err}
        except:
            err = 'Exception on QueuedJobsResouce.index'
            cherrypy.response.status = 500
            logger.log(err, severity=logging.ERROR, traceback=True)
            logger.log(err, severity=logging.ERROR,
                       logfile='error', traceback=True)
            r_code = {'err': err}

        return r_code
