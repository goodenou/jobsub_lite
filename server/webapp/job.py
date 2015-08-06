import base64
import random
import os
import re
import cherrypy
import logger
import sys
import StringIO
from datetime import datetime
from shutil import copyfileobj

from tempfile import NamedTemporaryFile
from util import  mkdir_p
from auth import check_auth, x509_proxy_fname
from jobsub import is_supported_accountinggroup
from jobsub import execute_job_submit_wrapper
from jobsub import JobsubConfig
from jobsub import create_dir_as_user
from jobsub import move_file_as_user
from jobsub import condor_bin
from jobsub import run_cmd_as_user
from format import format_response
from condor_commands import condor
from condor_commands import constructFilter, ui_condor_q, schedd_list
from sandbox import SandboxResource
from history import HistoryResource
from dag import DagResource
from queued_long import QueuedLongResource
from queued_dag import QueuedDagResource



@cherrypy.popargs('job_id','action_user')
class AccountJobsResource(object):
    def __init__(self):
        cherrypy.request.role = None
        cherrypy.request.username = None
        cherrypy.request.vomsProxy = None
        self.sandbox = SandboxResource()
        self.history = HistoryResource()
        self.dag = DagResource()
        self.long = QueuedLongResource()
        self.dags = QueuedDagResource()
        self.condorActions = {
            'REMOVE': condor.JobAction.Remove,
            'HOLD': condor.JobAction.Hold,
            'RELEASE': condor.JobAction.Release,
        }
        self.condorCommands = {
            'REMOVE': 'condor_rm',
            'HOLD': 'condor_hold',
            'RELEASE': 'condor_release',
        }


    def doGET(self, acctgroup, job_id, kwargs):
        """ Serves the following APIs:

            Query a single job. Returns a JSON map of the ClassAd 
            object that matches the job id
            API is /jobsub/acctgroups/<group_id>/jobs/<job_id>/

            Query list of jobs. Returns a JSON map of all the ClassAd 
            objects in the queue
            API is /jobsub/acctgroups/<group_id>/jobs/
        """
        uid = kwargs.get('user_id')
        filter = constructFilter(acctgroup,uid,job_id)
        logger.log('filter=%s'%filter)
        q=ui_condor_q(filter)
        all_jobs=q.split('\n')
        if len(all_jobs)<1:
            logger.log('condor_q %s returned no jobs'%filter)
            err = 'Job with id %s not found in condor queue' % job_id
            rc={'err':err}
        else:
            rc={'out':all_jobs}

        return rc


    def doDELETE(self, acctgroup, job_id=None, user=None):
        rc = {'out': None, 'err': None}

        rc['out'] = self.doJobAction(
                            acctgroup, job_id=job_id, user=user,
                            job_action='REMOVE')

        return rc


    def doPUT(self, acctgroup, job_id=None, user=None,  **kwargs):
        """
        Executed to hold and release jobs
        """

        rc = {'out': None, 'err': None}
        job_action = kwargs.get('job_action')

        if job_action and job_action.upper() in self.condorCommands:
            rc['out'] = self.doJobAction(
                                acctgroup, job_id=job_id, user=user,
                                job_action=job_action.upper())
        else:

            rc['err'] = '%s is not a valid action on jobs' % job_action

        logger.log(rc)

        return rc


    def doPOST(self, acctgroup, job_id, kwargs):
        """ Create/Submit a new job. Returns the output from the jobsub tools.
            API is /jobsub/acctgroups/<group_id>/jobs/<job_id>/
        """

        if job_id is None:
            child_env = os.environ.copy()
            jobsubConfig = JobsubConfig()
            logger.log('job.py:doPost:kwargs: %s' % kwargs)
            jobsub_args = kwargs.get('jobsub_args_base64')
            jobsub_client_version = kwargs.get('jobsub_client_version')
            jobsub_client_krb5_principal = kwargs.get('jobsub_client_krb5_principal','UNKNOWN')
            if jobsub_args is not None:

                jobsub_args = base64.urlsafe_b64decode(str(jobsub_args)).rstrip()
                logger.log('jobsub_args: %s' % jobsub_args)
                jobsub_command = kwargs.get('jobsub_command')
                role  = kwargs.get('role')
                logger.log('job.py:doPost:jobsub_command %s' %(jobsub_command))
                logger.log('job.py:doPost:role %s ' % (role))

                command_path_acctgroup = jobsubConfig.commandPathAcctgroup(acctgroup)
                mkdir_p(command_path_acctgroup)
                command_path_user = jobsubConfig.commandPathUser(acctgroup,
                                                                 cherrypy.request.username)
                # Check if the user specific dir exist with correct
                # ownership. If not create it.
                jobsubConfig.initCommandPathUser(acctgroup, cherrypy.request.username)

                ts = datetime.now().strftime("%Y-%m-%d_%H%M%S.%f")
                uniquer=random.randrange(0,10000)
                workdir_id = '%s_%s' % (ts, uniquer)
                command_path = os.path.join(command_path_acctgroup, 
                                            cherrypy.request.username, workdir_id)
                logger.log('command_path: %s' % command_path)
                child_env['X509_USER_PROXY'] = x509_proxy_fname(cherrypy.request.username,
                                                                 acctgroup, role)
                # Create the job's working directory as user 
                create_dir_as_user(command_path_user, workdir_id,
                                   cherrypy.request.username, mode='755')
                if jobsub_command is not None:
                    command_file_path = os.path.join(command_path,
                                                     jobsub_command.filename)
                    child_env['JOBSUB_COMMAND_FILE_PATH']=command_file_path
                    cf_path_w_space = ' %s'%command_file_path
                    logger.log('command_file_path: %s' % command_file_path)
                    # First create a tmp file before moving the command file
                    # in place as correct user under the jobdir
                    tmp_file_prefix = os.path.join(jobsubConfig.tmpDir,
                                                   jobsub_command.filename)
                    tmp_cmd_fd = NamedTemporaryFile(prefix="%s_"%tmp_file_prefix,
                                                    delete=False)
                    copyfileobj(jobsub_command.file, tmp_cmd_fd)

                    tmp_cmd_fd.close()
                    move_file_as_user(tmp_cmd_fd.name, command_file_path, cherrypy.request.username)
                    #with open(command_file_path, 'wb') as dst_file:
                    #    copyfileobj(jobsub_command.file, dst_file)

                    # replace the command file name in the arguments with 
                    # the path on the local machine.  
                    command_tag = '\ \@(\S*)%s' % jobsub_command.filename
                    jobsub_args = re.sub(command_tag, cf_path_w_space, jobsub_args)
                    logger.log('jobsub_args (subbed): %s' % jobsub_args)

                jobsub_args = jobsub_args.split(' ')
                rc = execute_job_submit_wrapper(
                         acctgroup=acctgroup, username=cherrypy.request.username,
                         jobsub_args=jobsub_args, workdir_id=workdir_id,
                         role=role, jobsub_client_version=jobsub_client_version,
                         jobsub_client_krb5_principal=jobsub_client_krb5_principal,
                         child_env=child_env)
                if rc.get('out'):
                    for line in rc['out']:
                        if 'jobsubjobid' in line.lower():
                            logger.log(line)
                if rc.get('err'):
                    logger.log(rc['err'])
            else:
                # return an error because no command was supplied
                err = 'User must supply jobsub command'
                logger.log(err)
                rc = {'err': err}
        else:
            # return an error because job_id has been supplied but POST is for creating new jobs
            err = 'User has supplied job_id but POST is for creating new jobs'
            logger.log(err)
            rc = {'err': err}

        return rc
   

    @cherrypy.expose
    @format_response
    def default(self,kwargs):
        logger.log('kwargs=%s'%kwargs)
        return {'out':"kwargs=%s"%kwargs}

    @cherrypy.expose
    @format_response
    @check_auth
    def index(self, acctgroup, job_id=None, action_user=None, **kwargs):
        try:
            logger.log('job_id=%s action_user=%s'%(job_id,action_user))
            if job_id == 'user':
                job_id = None
            cherrypy.request.role = kwargs.get('role')
            cherrypy.request.username = kwargs.get('username')
            cherrypy.request.vomsProxy = kwargs.get('voms_proxy')
            if is_supported_accountinggroup(acctgroup):
                if cherrypy.request.method == 'POST':
                    #create job
                    rc = self.doPOST(acctgroup, job_id, kwargs)
                elif cherrypy.request.method == 'GET':
                    #query job
                    rc = self.doGET(acctgroup, job_id, kwargs)
                elif cherrypy.request.method == 'DELETE':
                    #remove job
                    rc = self.doDELETE(acctgroup, job_id=job_id, user=action_user)
                elif cherrypy.request.method == 'PUT':
                    #hold/release
                    rc = self.doPUT(acctgroup, job_id=job_id, user=action_user, **kwargs)
                else:
                    err = 'Unsupported method: %s' % cherrypy.request.method
                    logger.log(err)
                    rc = {'err': err}
            else:
                # return error for unsupported acctgroup
                err = 'AccountingGroup %s is not configured in jobsub' % acctgroup
                logger.log(err)
                rc = {'err': err}
        except:
            cherrypy.response.status = 500
            err = 'Exception on AccountJobsResource.index'
            logger.log(err, traceback=True)
            rc = {'err': err}
        if rc.get('err'):
            cherrypy.response.status = 500
        return rc


    def doJobAction(self, acctgroup, job_id=None, user=None, job_action=None):
        scheddList = []
        if job_id:
            #job_id is a jobsubjobid
            constraint = 'regexp("group_%s.*",AccountingGroup)' % (acctgroup)
            # Split the jobid to get cluster_id and proc_id
            stuff=job_id.split('@')
            schedd_name='@'.join(stuff[1:])
            logger.log("schedd_name is %s"%schedd_name)
            scheddList.append(schedd_name)
            ids = stuff[0].split('.')
            constraint = '%s && (ClusterId == %s)' % (constraint, ids[0])
            if (len(ids) > 1) and (ids[1]):
                constraint = '%s && (ProcId == %s)' % (constraint, ids[1])
        elif user:
            #job_id is an owner 
            constraint = '(Owner =?= "%s") && regexp("group_%s.*",AccountingGroup)' % (user,acctgroup)
            scheddList = schedd_list()

        logger.log('Performing %s on jobs with constraints (%s)' % (job_action, constraint))

                            
        child_env = os.environ.copy()
        child_env['X509_USER_PROXY'] = cherrypy.request.vomsProxy
        out = err = ''
        affected_jobs = 0
        regex = re.compile('^job_[0-9]+_[0-9]+[ ]*=[ ]*[0-9]+$')
        extra_err = ""
        for schedd_name in scheddList:
            try:
                cmd = [
                    condor_bin(self.condorCommands[job_action]), '-l',
                    '-name', schedd_name,
                    '-constraint', constraint
                ]
                out, err = run_cmd_as_user(cmd, cherrypy.request.username, child_env=child_env)
            except:
                #TODO: We need to change the underlying library to return
                #      stderr on failure rather than just raising exception
                #however, as we are iterating over schedds we don't want
                #to return error condition if one fails, we need to 
                #continue and process the other ones
                err="%s: exception:  %s "%(cmd,sys.exc_info()[1])
                logger.log(err,traceback=1)
                extra_err = extra_err + err
                #return {'out':out, 'err':err}
            out = StringIO.StringIO('%s\n' % out.rstrip('\n')).readlines()
            for line in out:
                if regex.match(line):
                    affected_jobs += 1
        retStr = "Performed %s on %s jobs matching your request %s" % (job_action, affected_jobs, extra_err)
        return retStr
