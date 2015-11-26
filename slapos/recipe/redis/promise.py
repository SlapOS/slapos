#! /usr/bin/env python
# -*- coding: utf-8 -*-

import slapos.recipe.redis.MyRedis2410 as redis
import sys

def main(args):
  host = args['host']
  port = int(args['port'])
  unixsocket = args['unixsocket']
  try:
    r = redis.Redis(host=host, port=port, unix_socket_path=unixsocket, db=0)
    r.publish("Promise-Service","SlapOS Promise")
    r.connection_pool.disconnect()
    sys.exit(0)
  except Exception, e:
    print str(e)
    sys.exit(1)