# Restart openvpn and slapos-node, this script will wait for ipv6 to
# be ready and run slapformat. After the first run of slapformat, the
# server on which slapformat was run and its partitions should appear
# on www.slapos.org.

# for debug installer
# trap "sleep 30" EXIT

function is_openvpn_disconnected()
{
    getmac /V /FO list | grep "$IPV6INTERFACE" > /dev/null
    # return $?
    #   0 (false), connected
    #   1 (true), disconnected or disabled
}

# get connection name by IF_GUID
function get_connection_name()
{
     key='\HKLM\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002bE10318}'
     echo $(regtool -q get "$key\\$IPV6INTERFACE\Connection\Name")
}

#
# This script will be executed background.
#
SLAPOSCFG=/etc/slapos/slapos.cfg
OPENVPNHOME=/opt/openvpn
OPENVPNCFG=vifib.ovpn
LOGFILE=openvpn-vifib.log

# Startup openvpn if necessary
echo Check ipv6 interface
IPV6INTERFACE=$(grep "^\\s*ipv6_interface\\s*=\\s*[-{}0-9a-zA-Z]\+" $SLAPOSCFG | \
    sed -e "s/\\s*ipv6_interface\\s*=\\s*//g"| sed -e "s/ //g")
echo ipv6 interface is $IPV6INTERFACE

if [[ "$IPV6INTERFACE" != "" ]] ; then
    echo Check Vifib OpenVPN status ...

    # if openvpn is not up, start it
    is_openvpn_disconnected
    if (( $? )) ; then
        cd $OPENVPNHOME/config
        ./openvpn.exe --log "$LOGFILE" --dev-node $IPV6INTERFACE --config $OPENVPNCFG &
        # make sure the last backgroud process is openvpn
        ps -s -p "$i" | grep "config/openvpn" > /dev/null
        (( $? )) || OPENVPN_PID=$!
    fi
    # waiting for openvpn up, no more than 3 minutes 
    for (( i = 1; i < 6; i += 1 )) ; do
        is_openvpn_disconnected
        (( $? )) || break        
        echo Vifib OpenVPN is down, re-try after 10 seconds \($i of 6\) ...
        sleep 10
    done

    # last check
    is_openvpn_disconnected
    if (( $? )) ; then
        if [[ "$OPENVPN_PID" != "" ]] ; then
            echo Kill process of Vifib OpenVPN: $OPENVPN_PID
            kill -9 $OPENVPN_PID
        fi
        echo Error: Vifib OpenVPN can not be up, check your network and try it later.
        exit 1
    fi
    echo Vifib OpenVPN is up on \"$(get_connection_name)\"
    echo Vifib OpenVPN Process Info:
    ps -s -p ${OPENVPN_PID:-*}
    [ "$OPENVPN_PID" == "" ] || disown
    # kill -9 $OPENVPN_PID
fi

cd /opt/slapos
which slapformat 2>/dev/null 1>/dev/null
if (( $? )) ; then    
    source ./environment.sh
fi

# Run slapformat
echo Running slapformat to initialize slapos node ... 
echo bin/slapformat -c --now $SLAPOSCFG
echo 
# bin/slapformat -c --now $SLAPOSCFG
echo 
echo Now slapformat finished.
