#!/bin/bash

# DANGEROUS: this script will clear all existing iptables rules!

# This script will automatically set up:
# - IPv4 and IPv6 port forwarding from ports 25 and 587 to the right port (10025 by default) on the internal SMTP server
# - MASQUERADE rules to ensure proper routing of packets to external relays

# Clear all existing rules first
iptables -F
iptables -t nat -F
iptables -t mangle -F
iptables -X
iptables -t nat -X
iptables -t mangle -X

ip6tables -F
ip6tables -t nat -F
ip6tables -t mangle -F
ip6tables -X
ip6tables -t nat -X
ip6tables -t mangle -X

# this should not be modified
PORTS="25 587"

# these come from smtp-ipv4-internal, smtp-ipv6, and smtp-port from the relay instance
IPV4="10.0.62.65"
IPV6="2a11:9ac0:2f::b"
DEST="10025"

# this is specific to the machine
IFACE="enp1s0"

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

for PORT in $PORTS; do
    iptables -t nat -A PREROUTING -p tcp --dport $PORT -j DNAT --to-destination ${IPV4}:${DEST}
    iptables -t nat -A POSTROUTING -p tcp -d ${IPV4} --dport ${DEST} -j MASQUERADE
    # this one ensures packets sent from the local IP are NATted properly (otherwise it won't be able to send stuff outside)
    iptables -t nat -A POSTROUTING -s ${IPV4} -o ${IFACE} -j MASQUERADE
    iptables -A FORWARD -p tcp -d ${IPV4} --dport ${DEST} -j ACCEPT
done

for PORT in $PORTS; do
    ip6tables -t nat -A PREROUTING -p tcp --dport $PORT -j DNAT --to-destination [${IPV6}]:${DEST}
    ip6tables -t nat -A POSTROUTING -p tcp -d ${IPV6} --dport ${DEST} -j MASQUERADE
    ip6tables -A FORWARD -p tcp -d ${IPV6} --dport ${DEST} -j ACCEPT
done
