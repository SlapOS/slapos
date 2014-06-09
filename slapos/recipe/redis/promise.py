#! /usr/bin/env python
# -*- coding: utf-8 -*-

import slapos.recipe.redis.MyRedis2410 as redis
import sys

def main(args):
  host = args['host']
  port = int(args['port'])
  password = None
  try:
    # use a passfile, we don't store it cleartext on the recipe
    if 'requirepass_file' in args:
      with open(args['requirepass_file']) as fin:
        password = fin.read()
    pool = redis.ConnectionPool(host=host, port=port, db=0, password=password)
    r = redis.Redis(connection_pool=pool)
    r.publish('Promise-Service', 'SlapOS Promise')
    pool.disconnect()
    sys.exit(0)
  except Exception as e:
    print str(e)
    sys.exit(1)
