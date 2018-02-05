def dummyZBigArrayProcessing(self, id):
  import numpy as np
  from random import randrange, sample
  import transaction
  module = self['data_array_module']
  try:
    array = module[id]
  except KeyError:
    array = module.newContent(id, 'Data Array')
    array.initArray(shape=(0, 64), dtype=np.int32)
    transaction.commit()
  note = array.getPath() + '/new_data'
  array = array.getArray()
  rows, cols = array.shape

  y = xrange(cols)
  n = 10 * (2<<20) // (cols*4)
  z = np.ndarray(shape=(n, cols), dtype=array.dtype)
  for row in z:
    for i in sample(y, 8):
      row[i] = randrange(0, 1000)

  while 1:
    txn = transaction.begin()
    np.random.shuffle(z)
    rows += n
    array.resize((rows, cols))
    array[-n:] = z
    txn.note(note)
    txn.commit()
