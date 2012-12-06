##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
# for debug installer
# trap "sleep 30" EXIT

function usage()
{
    echo "Usage: configure.sh COMPUTER_ID [ KEY CERTIFICATE ]
    
  For example:
 
    $ /configure.sh COMP-161
 
    $ /configure.sh COMP-161 ~/computer.key ~/computer.crt"
}    

# return all the interface's GUID
function get_all_interface()
{    
    /opt/slapos/bin/py -c "from netifaces import interfaces
print '\n'.join(interfaces())"
}

# return GUID of physical netcard only
#
# Get the value of Characteristics of each interface,
# 
#    Characteristics & NCF_VIRTUAL == NCF_VIRTUAL
#    Characteristics & NCF_PHYSICAL == NCF_PHYSICAL
#    
function get_all_physical_netcard()
{
    local -r NCF_VIRTUAL=1
    local -r NCF_PHYSICAL=4
    local -r NCF_HIDDEN=8
    local -r NCF_HAS_UI=0x80
    local -r NCF_EXPECTED=$((NCF_PHYSICAL | NCF_HAS_UI))
    key='\HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002bE10318}'
    
    for subkey in $(regtool -q list "$key") ; do
        local -i flags=$(regtool -q get "$key\\$subkey\Characteristics")
        if (( (flags & NCF_EXPECTED) == NCF_EXPECTED )) ; then
            echo $(regtool -q get "$key\\$subkey\NetCfgInstanceId")
        fi
    done
}

#
# DriverDesc == TAP-Win32 Adapter V9
#
function get_openvpn_tap_interface()
{
    key='\HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002bE10318}'
    for subkey in $(regtool -q list "$key") ; do
        desc=$(regtool -q get "$key\\$subkey\DriverDesc")
        if [[ "$desc" == "TAP-Win32 Adapter V9" ]] ; then
            echo $(regtool -q get "$key\\$subkey\NetCfgInstanceId")
            break
        fi
    done
}

# get connection name by IF_GUID
function get_connection_name()
{
     key='\HKLM\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002bE10318}'
     echo $(regtool -q get "$key\\$IF_GUID\Connection\Name")
}

# tell the ip version
# 
#     0   None
#     1   ipv4
#     2   ipv6
#     3   mixed
#     
function get_local_ip_version()
{
    gateways=`ipconfig /all | grep "Gateway" | sed -e "s/^\\s\+Default Gateway[. :]\+//g"`
    ipv4flag=$(echo $gateways | grep ".")
    ipv6flag=$(echo $gateways | grep ":")
    if [[ "$ipv4flag" != "" ]] ; then
        local_ip_version=$((local_ip_version | 1))
    fi
    if [[ "$ipv6flag" != "" ]] ; then
        local_ip_version=$((local_ip_version | 2))
    fi
}

#
# Tell by getmac, if GUID can be found, it's ok, else disabled or not connected
function get_interface_state()
{
  getmac /V /FO list | grep "${INTERFACENAME}"
  return $?
}

# test code
# slist=$(get_all_physical_netcard)
# echo physical netcards: $slist

# for s in $slist ; do
#     INTERFACE_NAME=$s
#     echo conn name is $(get_connection_name)
# done

# get_local_ip_version
# echo version is $local_ip_version

# for s in $(get_all_interface) ; do
#     INTERFACE_NAME=$s
#     get_connection_name
#     echo conn name is $(get_connection_name)
# done

# echo openvpn tap interface is $(get_openvpn_tap_interface)

# exit 0

#
# main entry, first initialize variable
#
WINSYS32HOME="$(/usr/bin/cygpath -S -w)"
CYGWINSYS32HOME="$(/usr/bin/cygpath -S)"

DESTKEYFILE=/etc/slapos/ssl/computer.key
DESTCERTFILE=/etc/slapos/ssl/computer.crt
IPV6=${CYGWINSYS32HOME}/ipv6.exe
NETSH=${CYGWINSYS32HOME}/netsh.exe
IPCONFIG=${CYGWINSYS32HOME}/ipconfig.exe
GETMAC=${CYGWINSYS32HOME}/getmac.exe
OPENVPNHOME=/opt/openvpn
SLAPOSCFG=/etc/slapos/slapos.cfg

declare -i local_ip_version=0
error_code=0

# remove startup item first.
RUNKEY='\HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
SLAPOSNODEINIT=SlapOSNodeInit
regtool -q unset "$RUNKEY\\$SLAPOSNODEINIT"

if (( $# != 1 && $# != 3 )) ; then
  usage
  exit 1
fi

which slapformat 2>/dev/null 1>/dev/null
if (( $? )) ; then
    echo "Run this script must be in the SlapOS environments, do first:
    \$ cd /opt/slapos
    \$ source environment.sh"
    cd /opt/slapos
    source ./environment.sh
fi

COMPUTERID=$1
if [[ "$COMPUTERID" == "" ]] ; then
    grep "^\\s\+computer_id\\s\+=\\s\+[-a-zA-Z0-9]\+" $SLAPOSCFG
    if (( $? )) ; then
        echo No computer id.
        error_code=1
    fi
elif [[ ${COMPUTERID:0:5} != "COMP-" ]] ; then
    echo Invalide computer id \"$COMPUTERID\", it should be like \"COMP-XXX\"
    error_code=1
fi

if [[ "$2" != "" ]] ; then
    KEYFILE=$(cygpath -u "$2")
fi
if [[ "$3" != "" ]] ; then
    CERTFILE=$(cygpath -u "$3")
fi

# check netsh
[ -f ${NETSH} ] || (echo "Error: unable to find command: netsh" && exit 1)
[ -f ${IPCONFIG} ] || (echo "Error: unable to find command: ipconfig" && exit 1)
[ -f ${GETMAC} ] || (echo "Error: unable to find command: getmac" && exit 1)
[ -f ${IPV6} ] || (echo "Error: unable to find command: ipv6" && exit 1)

# check ipv6
get_local_ip_version
if (( (local_ip_version & 2) == 0 )) ; then
    echo "Install ipv6, maybe you need specify the location of windows setup pacakge ..."
    netsh interface ipv6 install
fi

# get GUID of the first physics netcard
for IPINTERFACE in $(get_all_physical_netcard) ; do
  break ;
done

# check to support native ipv6, if not, openvpn is necessary
IPV6INTERFACE=
declare -i openvpn_required=$((local_ip_version != 2))
if (( openvpn_required )) ; then
    echo OpenVPN is required because of no native ipv6.

    echo Check OpenVPN TAP Driver ...
    getmac -v -Fo list | grep "TAP-Win32 Adapter V9" > /dev/null

    if (( $? )) ; then
        echo Install OpenVPN TAP driver as tap0901 ...
        (cd ${OPENVPNHOME}/driver ; ./tapinstall.exe install OemWin2k.inf tap0901)
        echo OpenVPN TAP driver Installed.
    else
        echo OpenVPN TAP Driver has been installed before.
    fi

    # echo Try to get OpenVPN TAP driver\'s connection name ...
    # CONNAME=$(getmac -v -Fo list | grep -B1 "TAP-Win32 Adapter V9" | \
    #            sed -e "2d" | sed -e "s/Connection Name:\\s+//g")
    # if [[ "${CONNAME}" == "" ]] ; then
    #     echo "Can't find connection name of TAP driver."
    #     exit 1
    # fi 
    # echo TAP driver\'s connection name is "${CONNAME}"

    echo Try to get OpenVPN TAP driver\'s GUID ...
    # IPV6INTERFACE=$(ipv6 if | \
    #     grep -A1 "^Interface [0-9]+: Ethernet: ${CONNECTION}" | \
    #     sed -e "1d" | sed -e "s/\\s+Guid\\s+//g")
    IPV6INTERFACE=$(get_openvpn_tap_interface)
    if [[ "${IPV6INTERFACE}" == "" ]] ; then
        echo "Can't get interface name of TAP driver."
        exit 1
    fi 
    echo Got it: ${IPV6INTERFACE}
    
fi

# check key, crt
if [[ -f "${KEYFILE}" && ! "${KEYFILE}" -ef ${DESTKEYFILE} ]] ; then
    echo Copy ${KEYFILE} to ${DESTKEYFILE}
    cp ${KEYFILE} ${DESTKEYFILE}
    chmod 644 ${DESTKEYFILE}
fi

if [[ -f "${CERTFILE}" && ! "${CERTFILE}" -ef ${DESTCERTFILE} ]] ; then
    echo Copy ${CERTFILE} to ${DESTCERTFILE}
    cp ${CERTFILE} ${DESTCERTFILE}
    chmod 644 ${DESTCERTFILE}
fi

[ -f ${DESTCERTFILE} ] || (echo "Error: unable to find $DESTCERTFILE file." && error_code=1)
[ -f ${DESTKEYFILE} ] || (echo "Error: unable to find $DESTKEYFILE file." && error_code=1)

# generate /etc/slapos/slapos.cfg
[ "${COMPUTERID}" == "" ] || \
    sed -i "s/^\\s*computer_id.*$/computer_id = ${COMPUTERID}/g" ${SLAPOSCFG}
[ "${IPINTERFACE}" == "" ] || \
    sed -i "s/^\\s*interface_name.*$/interface_name = ${IPINTERFACE}/g" ${SLAPOSCFG}
[ "${IPV6INTERFACE}" == "" ] || \
    sed -i "s/^#\?\\s*ipv6_interface.*$/ipv6_interface = ${IPV6INTERFACE}/g" ${SLAPOSCFG}

echo Set slapos init script as Windows startup item.
regtool -q set "$RUNKEY\\$SLAPOSNODEINIT" "\"$(cygpath -w /usr/bin/sh)\" --login -i /slapnode-init.sh"
(( $? )) && echo Fail to set init script as startup item.

if (( error_code )) ; then
    echo Fail to configure SlapOS node, you need run this scripts again after fix the problems.
else
    echo Configure SlapOS node successfully.
fi

exit $error_code
