#! /bin/bash

#switch work directory
SCRIPT_PATH=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPT_DIR=${SCRIPT_PATH%/*}
if [ -z "$SCRIPT_DIR" ]; then
    SCRIPT_DIR="/"
fi
cd "${SCRIPT_DIR}"


PROC_ENV="env IVENTOY_API_ALL=1"
PROJ_DIR=$PWD
PROJ_EXEC=$PROJ_DIR/lib/iventoy
PROJ_PID=/var/run/iventoy.pid

uid=$(id -u)
if [ $uid -ne 0 ]; then
    echo "Please use sudo or run the script as root."
    exit 1
fi

if [ "$1" = '-A' ]; then
    shift
fi

if [ "$1" = '-R' ]; then
    shift
    PROC_ENV="$PROC_ENV IVENTOY_AUTO_RUN=1"
fi


if echo $1 | grep -P -q '^(start|stop|status)$'; then
    :
else
    echo -e "\nUsage: $0 { start | stop | status }\n"
    exit 1
fi

iventoy_get_running_pid() {
    local PID
    local FILE
    
    if [ -f $PROJ_PID ]; then
        if grep -q '[0-9]' $PROJ_PID; then
            PID=$(cat $PROJ_PID)
            if [ -e /proc/$PID/exe ]; then
                FILE=$(readlink -f /proc/$PID/exe)
                if echo $FILE | grep -q '/iventoy$'; then
                    echo $PID
                    return
                fi
            fi
        fi
    fi
    
    echo 0
}


start() {
    local PID
    local RETVAL
    
    PID=$(iventoy_get_running_pid)
    if [ $PID -ne 0 ]; then
        echo "[ERROR] iventoy is already running. PID=$PID"
        exit 1
    fi

    cd $PROJ_DIR
    $PROC_ENV $PROJ_EXEC
    RETVAL=$?
    
    if [ $RETVAL -eq 0 ]; then
        PID=$(iventoy_get_running_pid)
        echo "iventoy start SUCCESS PID=$PID"
        echo ""
        echo "Please open your browser and visit http://127.0.0.1:26000 or http://x.x.x.x:26000 (x.x.x.x is any valid IP address)"        
        echo ""
    else
        echo "iventoy start FAILED"
    fi
}

stop() {
    local PID
    local RETVAL
    
    PID=$(iventoy_get_running_pid)
    if [ $PID -eq 0 ]; then
        echo "[ERROR] iventoy is not running"
        exit 1
    fi
    
    kill -15 $PID
}

status() {
    local PID

    PID=$(iventoy_get_running_pid)
    if [ $PID -ne 0 ]; then
        echo "iventoy is running, PID=$PID"
        echo ""
    else
        echo "iventoy is not running."
    fi
}

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  status)
        status
        ;;  
  *)
        echo -e "\nUsage: $0 { start | stop | status }\n"
        exit 2
esac

exit $?
