/******************************************************************************
 *
 * Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
 *
 * WARNING: This program as such is intended to be used by professional
 * programmers who take the whole responsibility of assessing all potential
 * consequences resulting from its eventual inadequacies and bugs
 * End users who are looking for a ready-to-use solution with commercial
 * guarantees and support are strongly adviced to contract a Free Software
 * Service Company
 *
 * This program is Free Software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 3
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 *
 ******************************************************************************/

package org.slapos.slap;

import java.util.HashMap;
import java.util.Map;

import org.slapos.slap.interfaces.IOpenOrder;

public class OpenOrder extends SlapDocument implements IOpenOrder {
	private ClientWrapper connection;
	
	public OpenOrder(ClientWrapper connection) {
		this.connection = connection;
	}

	//FIXME Java conventions
	public ComputerPartition request(String softwareRelease, String partition_reference,
			Map<String, Object> partition_parameter_kw, String software_type) {
		if (partition_parameter_kw == null) {
			partition_parameter_kw = new HashMap<String, Object>();
		}
		ComputerPartition cp = new ComputerPartition(connection);
		cp.setSoftware_release(softwareRelease);
		cp.setPartition_reference(partition_reference);
		cp.setParameter_dict(partition_parameter_kw);

		if (software_type != null) {
			cp.setSoftware_type(software_type);
		}

		// Sends it, reads response
		return cp.sendRequest(cp);
	}
}