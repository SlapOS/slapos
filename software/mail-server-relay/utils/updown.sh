#!/bin/bash

# Bring a mail relay up or down for maintenance.
#
# iptables -L -t nat can be used to verify the current state of the rules.
#
# When "down", inbound SMTP connections on ports 25 and 587 are immediately
# rejected with a TCP RST so that remote MTAs try the next MX host without
# waiting for a timeout.
#
# Usage:
#   ./updown.sh down <ipv4> <ipv6>   # reject inbound SMTP
#   ./updown.sh up   <ipv4> <ipv6>   # accept inbound SMTP again

set -eu

ACTION="$1"
IPV4="$2"
IPV6="$3"

PORTS="25 587"

case "$ACTION" in
  down)
    for PORT in $PORTS; do
      iptables  -I INPUT -d "$IPV4" -p tcp --dport "$PORT" -j REJECT --reject-with tcp-reset
      ip6tables -I INPUT -d "$IPV6" -p tcp --dport "$PORT" -j REJECT --reject-with tcp-reset
    done
    echo "Relay $IPV4 / $IPV6 is now DOWN (ports $PORTS rejected)"
    ;;
  up)
    for PORT in $PORTS; do
      iptables  -D INPUT -d "$IPV4" -p tcp --dport "$PORT" -j REJECT --reject-with tcp-reset
      ip6tables -D INPUT -d "$IPV6" -p tcp --dport "$PORT" -j REJECT --reject-with tcp-reset
    done
    echo "Relay $IPV4 / $IPV6 is now UP (ports $PORTS accepted)"
    ;;
  *)
    echo "Usage: $0 {up|down} <ipv4> <ipv6>" >&2
    exit 1
    ;;
esac
