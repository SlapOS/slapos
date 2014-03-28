#!/usr/bin/env python

#Print Network address and generate range of 60 IPV4s for Openstack floatings IPs

import os
import sys
from netaddr import IPNetwork

def getNetwork(ipaddress, mask):
	net = str(IPNetwork('%s/%s' % (ipaddress, mask)).cidr.network)
	net_cidr = str(IPNetwork('%s/%s' % (ipaddress, mask)).cidr)
	items = ipaddress.split('.')
	base = "%s.%s.%s" % (items[0], items[1], items[2])
	if int(items[3])+60 < 254:
		ranges = "%s.%s %s.%s" % (base, (int(items[3])+1), 
			base, (int(items[3])+60))
	else:
		ranges = "%s.%s %s.%s" % (base, (int(items[3])-1), 
			base, (int(items[3])-60))
	return net + " " + net_cidr + " " + ranges
	
if __name__ == '__main__':
	print getNetwork(sys.argv[1], sys.argv[2])
	exit(0)