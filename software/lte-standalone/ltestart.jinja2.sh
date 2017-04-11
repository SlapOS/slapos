#!/bin/bash
# Copyright (C) 2012-2016 Amarisoft
# LTE system starter version 2016-10-13

##################
# Default config #
##################
source {{ directory['etc'] }}/ltestart.conf


# Redirect IO
exec 0>&-
exec 1>>$LOG_FILE
exec 2>>$LOG_FILE


# Termination
function EndOfLTE {

    echo "* Stopping LTE service"

    # Quit programs and screen windows
    for i in 0 1 2 3 ; do
        sleep 0.2
        {{ screen_bin }} -S lte -p $i -X stuff $'\nquit\n'
    done

    # Quit
    for i in 0 1 2 3 ; do
        sleep 0.2
        {{ screen_bin }} -S lte -p $i -X stuff $'exit\n'
    done

    # Save logs
    ltelogs.sh {{ directory['log'] }}/ims.log \
               {{ directory['log'] }}/mme.log \
               {{ directory['log'] }}/enb0.log \
               {{ directory['log'] }}/mbmsgw.log

    echo "* LTE service stopped"
    exit 0
}
trap EndOfLTE KILL INT TERM

# Send command to window
function cmd
{
    win="$1"

    {{ screen_bin }} -S lte -p $win -X stuff $'\n' # Empty line in case of

    while [ "$2" != "" ] ; do
        {{ screen_bin }} -S lte -p $win -X stuff "$2"$'\n'
        shift
    done
}


# Path for multi environment support
export PATH="$PATH:/bin/:/usr/bin/:/usr/local/bin"

echo "* Start LTE service"

# Core dumps
#< In production we don't really want core dumps
#< ulimit -c unlimited
#< echo "/tmp/core" > /proc/sys/kernel/core_pattern

# Logs
LOG_CFG="file.rotate=$LOG_SIZE,file.path=$LOG_PATH"

# Init state
MME_STATE=""
ENB_STATE=""
MBMS_STATE=""
UE_STATE=""

# Poll
while [ 1 ] ; do

    ##########
    # Screen #
    ##########
    SCREEN=$({{ screen_bin }} -ls lte | grep -w lte)
    if [ "$SCREEN" = "" ] ; then
        echo "* Create screen and initialize windows"

        # start a new screen session
        {{ screen_bin }} -dm -S lte

        # Add windows
        sleep 0.1; {{ screen_bin }} -S lte -X screen
        sleep 0.1; {{ screen_bin }} -S lte -X screen
        sleep 0.1; {{ screen_bin }} -S lte -X screen

        cmd 0 'printf "\\033k%s\\033\\\\" MME' 'clear'
        cmd 1 'printf "\\033k%s\\033\\\\" eNB' 'clear'
        cmd 2 'printf "\\033k%s\\033\\\\" MBMS' 'clear'
        cmd 3 'printf "\\033k%s\\033\\\\" IMS' 'clear'

        # Set HOME for UHD to find calibration files
        cmd $ENB_WIN "export HOME={{ buildout['directory'] }}"
    fi

    # Update date
    DATE=$(date -u +%Y%m%d-%H:%M:%S | sed -e "s/ /-/g")

    S1CONNECT=0

    #######
    # MME #
    #######
    if [ -e "$MME_PATH/ltemme" ] ; then
        # Init
        if [ "$MME_STATE" != "done" ] ; then

            echo "* Initialize MME with option '$MME_INIT'"
            $MME_PATH/lte_init.sh $MME_INIT
            if [ "$?" = "0" ] ; then
                echo "* MME initialized"
                MME_STATE="done"
            else
                # Configure at least locally to allow LTE local connections
                if [ "$MME_STATE" != "LOCAL" ] ; then
                    echo "* Initialize MME with local interface"
                    $MME_PATH/lte_init.sh lo
                    MME_STATE="LOCAL"
                fi
            fi
        fi

        MME=$(pgrep ltemme)
        if [ "$MME" = "" ] ; then

            # "MME not running, start it here"
            echo "* Starting MME"
            ltelogs.sh {{ directory['log'] }}/mme.log
            cmd $MME_WIN "cd $MME_PATH" "./ltemme config/mme.cfg" "log $LOG_CFG"

            # Wait for MME to start
            sleep 0.5

            S1CONNECT=1
        fi

        #######
        # IMS #
        #######
        if [ -e "$IMS_PATH/lteims" ] ; then
            IMS=$(pgrep lteims)
            if [ "$IMS" = "" ]; then
                # IMS not running, start it here
                echo "* Starting IMS"
                ltelogs.sh {{ directory['log'] }}/ims.log
                cmd $IMS_WIN "cd $IMS_PATH" "./lteims config/ims.cfg" "log $LOG_CFG"

                sleep 0.5
                cmd $MME_WIN "imsconnect"
                cmd $IMS_WIN "t"
            fi
        fi
    fi

    #######
    # eNB #
    #######
    if [ -e "$ENB_PATH/lteenb" ] ; then
        # Init
        if [ "$ENB_STATE" != "done" ] ; then
            echo "* Initialize eNB with option '$ENB_INIT'"
            $ENB_PATH/lte_init.sh $ENB_INIT
            if [ "$?" = "0" ] ; then
                ENB_STATE="done"
            fi
        fi

        ENB=$(pgrep lteenb)
        if [ "$ENB" = "" ]; then
            # Test if Radio head is running to start eNB
            if [ -e "${ENB_PATH}/config/rf_driver/rrh_check.sh" ] ; then
                ${ENB_PATH}/config/rf_driver/rrh_check.sh $RRH_CFG
                RRH="$?"
            else
                RRH="0"
            fi
            if [ "$RRH" = "0" ] ; then
                # "eNodeB not running, start it here"
                echo "* Starting eNB"
                ltelogs.sh {{ directory['log'] }}/enb0.log
                cmd $ENB_WIN "cd $ENB_PATH" "./lteenb config/enb.cfg" "log $LOG_CFG" "t"
            fi

        else
            # Force S1 connection ?
            if [ "$S1CONNECT" = "1" ] ; then
                cmd "ENB" "cd $ENB_PATH" "s1connect" "t"
            fi
        fi
    fi

    ########
    # MBMS #
    ########
    if [ -d "$MBMS_PATH" ] ; then
        # Init
        if [ "$MBMS_STATE" != "done" ] ; then
            echo "* Initialize MBMSGW with option '$MBMS_INIT'"
            $MBMS_PATH/lte_init.sh $MBMS_INIT
            if [ "$?" = "0" ] ; then
                MBMS_STATE="done"
            fi
        fi

        MBMS=$(pgrep ltembmsgw)
        if [ "$MBMS" = "" ]; then
            # MBMS not running, start it here
            echo "* Starting MBMSGW"
            ltelogs.sh {{ directory['log'] }}/mbmsgw.log
            cmd $MBMS_WIN "cd $MBMS_PATH" "./ltembmsgw config/mbmsgw.cfg" "log $LOG_CFG"
        fi
    fi

    ######
    # UE #
    ######
    if [ -e "$UE_PATH/lteue" ] ; then
        # Init
        if [ "$UE_STATE" != "done" ] ; then
            echo "* Initialize UE"
            if [ -e "${UE_PATH}/config/rf_driver/rrh_check.sh" ] ; then
                ${UE_PATH}/config/rf_driver/rrh_check.sh $RRH_CFG
            fi
            $UE_PATH/lte_init.sh $UE_INIT
            if [ "$?" = "0" ] ; then
                UE_STATE="done"
            fi
        fi
    fi

    # Remove core dumps older than 30min
    find /tmp/ -name "core*" -mmin 30 | xargs rm -f

    # Compress logs if needed
    if [ "$LOG_GZIP" = "1" ] ; then
        LIST=$(find $LOG_PATH -type f -name "*log*" | grep -v "gz$")
        for i in $LIST ; do
            gzip $i
            break; # One by one as it may last a while
        done
    fi

    # Remove logs if too much
    while [ $(du -ks $LOG_PATH | cut -d $'\t' -f1) -gt $LOG_PERSISTENT_SIZE ] ; do
        FILES=$(ls -a $LOG_PATH)
        for i in $FILES ; do
            if [ -f $LOG_PATH/$i ] ; then
                rm $LOG_PATH/$i;
                break
            fi
        done
    done

    # 5s polling
    sleep 5

done
