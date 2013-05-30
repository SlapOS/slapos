#! /usr/bin/env python
# -*- coding: utf-8 -*-

import slapos.recipe.redis.MyRedis2410 as redis
import sys

def main(args):
  host = args['host']
  port = int(args['port'])
  try:
    pool = redis.ConnectionPool(host=host, port=port, db=0)
    r = redis.Redis(connection_pool=pool)
    r.publish("Promise-Service","SlapOS Promise")
    pool.disconnect()
    sys.exit(0)
  except Exception, e:
    print str(e)
    sys.exit(1)