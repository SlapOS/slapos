# Copyright (C) 2023  Nexedi SA and Contributors.
#
# This program is free software: you can Use, Study, Modify and Redistribute
# it under the terms of the GNU General Public License version 3, or (at your
# option) any later version, as published by the Free Software Foundation.
#
# You can also Link and Combine this program with other software covered by
# the terms of any of the Free Software licenses or any of the Open Source
# Initiative approved licenses and Convey the resulting work. Corresponding
# source of such a combination shall include the source code for all other
# software used.
#
# This program is distributed WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See COPYING file for full licensing terms.
# See https://www.nexedi.com/licensing for rationale and options.

import os

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, ORSTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))

# XXX

# XXX enb   - {sdr,lopcomm,sunwave}·2 - {cell_lte1fdd,2tdd, cell_nr1fdd,2tdd}  + peer·2 + peercell·2
# XXX uesim - {sdr,lopcomm,sunwave}·2

# XXX core-network - skip - verified by ors
