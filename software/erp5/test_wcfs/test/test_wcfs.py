##############################################################################
#
# Copyright (c) 2022 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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

from collections import namedtuple
import pytest
import numpy as np
from wendelin.bigarray.array_zodb import ZBigArray
from wendelin.lib.zodb import dbopen, dbclose
from wendelin.wcfs import join
from ZODB import DB
from golang import defer, func
import transaction


@pytest.fixture(scope="session")
def zurl(pytestconfig):
  return pytestconfig.getoption("zurl")


@func
def test_data_is_written_to_wcfs(zurl):
  _ = getRunner(zurl)
  @_
  def zarray(root):
    assert not hasattr(root, 'zarray')
    root.zarray = zarray = ZBigArray(shape=(4,), dtype=int)
    transaction.commit()
    zarray.append([0, 0, 0, 0])
    transaction.commit()
    return zarray

  defer(lambda: _(cleanup))
  def cleanup(root):
    del root.zarray; transaction.commit()

  wcfs = join(zurl); defer(wcfs.close)
  assert wcfs._read(zarray.zfile)
  stat = wcfs._stat(zarray.zfile)
  assert stat.st_blksize == zarray.zfile.blksize
  assert stat.st_size == zarray.zfile.blksize


@func
def test_array_read_write_modify(zurl):
  """Verify writing/reading ZBigArray to/from ZODB works."""
  _ = getRunner(zurl)
  @_
  def create_array_and_commit(root):
    assert not hasattr(root, 'zarray')
    root.zarray = ZBigArray(shape=(4,), dtype=int)
    transaction.commit()

  defer(lambda: _(cleanup))
  def cleanup(root):
    del root.zarray; transaction.commit()

  @_
  def verify_array_has_been_written_to_zodb(root):
    assert hasattr(root, 'zarray')
    assert root.zarray.shape, (4,)
    np.testing.assert_array_equal(root.zarray[:], [0,0,0,0])
  @_
  def mutate_array_and_commit(root):
    root.zarray[:][0] = 100; transaction.commit()
  @_
  def verify_mutation_has_been_written_to_zodb(root):
    assert root.zarray[:][0] == 100


def getRunner(zurl):
  @func
  def run(func):
    root = dbopen(zurl)
    defer(lambda: dbclose(root))
    return func(root)

  return run
