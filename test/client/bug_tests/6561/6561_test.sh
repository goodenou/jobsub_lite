#!/bin/sh

if [ "$1" = "" ]; then
    echo "usage $0 server script_to_submit [script args]"
    echo "test submission to jobsub client/server architecture"
    exit 0
fi
cd ../../
source ./setup_env.sh
cd -

export SERVER=https://${MACH}:8443

$EXEPATH/jobsub_submit.py $GROUP_SPEC --debug \
       $SERVER_SPEC $SUBMIT_FLAGS \
            -e SERVER --nowrapfile   file://6561.sh foo@bar.com

$EXEPATH/jobsub_submit.py $GROUP_SPEC \
       $SERVER_SPEC $SUBMIT_FLAGS \
           -g -e SERVER    file://6561.sh foo@bar.com
