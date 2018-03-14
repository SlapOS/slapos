#!/usr/bin/python
from __future__ import division, print_function
import os, struct
from random import lognormvariate

bigfile_chunk_size = 65536

def simulateFluentdIngestion(self, id, mu, sigma,
                             chunks_per_transaction=128):
  from time import time
  import transaction
  note = (self['portal_ingestion_policies']['scalability_test_unpack'].getPath()
          + '/ingest')
  module = self['data_stream_module']
  try:
    data_stream = module[id]
  except KeyError:
    data_stream = module.newContent(id, 'Data Stream')
    transaction.commit()

  pack = struct.Struct('!d').pack
  data = os.urandom(bigfile_chunk_size - 8)

  while 1:
    txn = transaction.begin()
    data_stream.appendData(''.join(
      (pack(time()) + data[:int(lognormvariate(mu, sigma))]
      ).ljust(bigfile_chunk_size, '\0')
      for _ in xrange(chunks_per_transaction)))
    txn.note(note)
    txn.commit()

if __name__ == '__main__':
  import sys
  mu, sigma = map(float, sys.argv[1:3])
  if sigma:
    try:
      n = int(sys.argv[3])
    except IndexError:
      n = 1000000
  else:
    n = 1
  x = sorted(min(int(lognormvariate(mu, sigma)), bigfile_chunk_size - 8)
             for _ in xrange(n))
  print((8 * n + sum(x)) / (bigfile_chunk_size * n))
  if n == 1:
    print(x[0] + 8)
  else:
    n //= 100
    if n:
      print(8 + x[n], '-', 8 + x[-n-1], '(99th percentile)')
    else:
      print(8 + x[0], '-', 8 + x[-1])
