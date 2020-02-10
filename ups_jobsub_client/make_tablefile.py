#!/usr/bin/env python
import os
import sys
import datetime
import string

version_template = """
FILE = version
PRODUCT = jobsub_client
VERSION = %s

#*************************************************
#
FLAVOR = NULL
QUALIFIERS = ""
  DECLARER = %s
  DECLARED = %s
  MODIFIER = %s
  MODIFIED = %s
  PROD_DIR = jobsub_client/%s/NULL
  UPS_DIR = ups
  TABLE_FILE = %s.table

"""

table_template = """


FILE=table
Product=jobsub_client

Flavor=ANY
QUalifiers=

Action=setup

    setupEnv()
    prodDir()
    envPrepend(PYTHONPATH, ${UPS_PROD_DIR},':' )
    envPrepend(PATH, ${UPS_PROD_DIR},':' )
    execute( "pyflavor"  , NO_UPS_ENV, JOBSUB_PYVER )
    execute( "ups setup  python_future_six_request -q ${JOBSUB_PYVER}", NO_UPS_ENV, PY_FUTURE_SOURCE )
    sourceRequired( ${PY_FUTURE_SOURCE}, NO_UPS_ENV )
    envUnSet( PY_FUTURE_SOURCE )

Action=unsetup

    envUnSet( JOBSUB_PYVER )
    execute ( "ups unsetup python_future_six_request", NO_UPS_ENV, _unsetup_py_six )
    sourceRequired( ${_unsetup_py_six}, NO_UPS_ENV )
    envUnSet( _unsetup_py_six )
    pathRemove(PYTHONPATH, ${UPS_PROD_DIR} )
    pathRemove(PATH, ${UPS_PROD_DIR})

    unproddir()
    unsetupenv()


"""

current_template = """
FILE = chain
PRODUCT = jobsub_client
CHAIN = current

#*************************************************
#
FLAVOR = NULL
VERSION = %s
QUALIFIERS = ""
  DECLARER = %s
  DECLARED = %s
  MODIFIER = %s
  MODIFIED = %s
"""

if __name__ == "__main__":

    vers = sys.argv[1]
    gmt = datetime.datetime.utcnow()
    dstr = "%s-%s-%s %s.%s.%s GMT" % (gmt.year, gmt.month, gmt.day, gmt.hour,
                                      gmt.minute, gmt.second)
    user = os.environ.get('USER')
    f = open("ups_db/jobsub_client/%s.table" % vers, 'w')
    f.write(table_template)
    f.close()

    version = version_template % (vers, user, dstr, user, dstr, vers, vers)
    f = open("ups_db/jobsub_client/%s.version" % vers, 'w')
    f.write(version)
    f.close()

    current = current_template % (vers, user, dstr, user, dstr)
    f = open("ups_db/jobsub_client/current.chain", 'w')
    f.write(current)
    f.close()
