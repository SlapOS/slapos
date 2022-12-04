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

import pytest
import numpy as np
from wendelin.bigarray.array_zodb import ZBigArray
from wendelin.lib.zodb import dbopen, dbclose
from wendelin.wcfs import join
from ZODB import DB
import transaction


@pytest.fixture(scope="session")
def zurl(pytestconfig):
  return pytestconfig.getoption("zurl")


def test_access_wcfs(zurl):
  wcfs = join(zurl)
  assert wcfs


def test_array_is_writeable_and_readable(zurl):
  """Verify writing/reading ZBigArray to/from ZODB works."""
  _ = getRunner(zurl)
  @_
  def create_array_and_commit(root):
    assert not hasattr(root, 'zarray')
    root.zarray = ZBigArray(shape=(4,), dtype=int)
    transaction.commit()
  @_
  def verify_array_has_been_written_to_zodb(root):
    assert hasattr(root, 'zarray')
    assert root.zarray.shape, (4,)
    assert root.zarray.shape, (4,)
    np.testing.assert_array_equal(root.zarray[:], [0,0,0,0])
  @_
  def mutate_array_and_commit(root):
    root.zarray[:][0] = 100; transaction.commit()
  @_
  def verify_mutation_has_been_written_to_zodb(root):
    assert root.zarray[:][0] == 100
  @_
  def cleanup(root):
    del root.zarray; transaction.commit()


def getRunner(zurl):
  def run(func):
    root = dbopen(zurl)
    func(root)
    dbclose(root)

  return run
