#!/bin/sh
if [ "$1" = "" ]; then
    echo "usage: $0 server [joblist] "
    echo " hold and relieve list of jobs on server"
    exit 0
fi
source ./setup_env.sh
JOBLIST=`echo "$@"|sed 's/\s\+/,/g'`

echo before
$EXEPATH/jobsub_q.py $GROUP_SPEC $SERVER_SPEC  
T1=$?
echo T1=$T1
echo holding joblist=${JOBLIST}
$EXEPATH/jobsub_hold.py $GROUP_SPEC $SERVER_SPEC  --jobid $JOBLIST --debug
T2=$?
echo T2=$T2
echo after hold
$EXEPATH/jobsub_q.py $GROUP_SPEC $SERVER_SPEC  
T3=$?
echo T3=$T3
echo releasing joblist=${JOBLIST}
$EXEPATH/jobsub_release.py $GROUP_SPEC $SERVER_SPEC  --jobid $JOBLIST --debug
T4=$?
echo T4=$T4
echo after release
$EXEPATH/jobsub_q.py $GROUP_SPEC $SERVER_SPEC  
T5=$?
echo T5=$T5
! (( $T1 || $T2 || $T3 || $T4 || $T5 ))
T6=$?

echo $0 exiting with status $T6
exit $T6
