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

import java.io.IOException;

import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.slapos.slap.interfaces.ISlap;

/*
Simple, easy to (un)marshall classes for slap client/server communication
 */

//TODO : https connection
//TODO : correct encoding?

class SlapDocument {}

class ResourceNotReady extends Exception {

	/**
	 * 
	 */
	private static final long serialVersionUID = -6398370634661469874L;}

class ServerError extends Exception {

	/**
	 * 
	 */
	private static final long serialVersionUID = 8414085299597106973L;}

/*
class ConnectionHelper:
  error_message_connect_fail = "Couldn't connect to the server. Please double \
check given master-url argument, and make sure that IPv6 is enabled on \
your machine and that the server is available. The original error was:"

  def getComputerInformation(self, computer_id):
    self.GET('/getComputerInformation?computer_id=%s' % computer_id)
    return xml_marshaller.loads(self.response.read())
 */

public class Slap implements ISlap {
	private String computerGuid;
	private ClientWrapper slaposMasterRestClient;

	public void initializeConnection(String slaposMasterUri) {
		if (slaposMasterRestClient != null) {
			System.out.println("Warning : Slap has already been initialized. Reinitializing..."); // TODO logger
		}
		this.slaposMasterRestClient = new ClientWrapper(slaposMasterUri);
		this.computerGuid = null;
	}

	@Override
	public void initializeConnection(String slapgridUri,
			String authentificationKey) {
		// TODO Auto-generated method stub

	}

	@Override
	public Computer registerComputer(String computerGuid) {
		this.computerGuid = computerGuid;
		return new Computer(getConnectionWrapper(), computerGuid);
	}

	/*
	 * Registers connected representation of software release and
	 * returns SoftwareRelease class object(non-Javadoc)
	 * @see org.slapos.slap.interfaces.ISlap#registerSoftwareRelease(java.lang.String)
	 */
	@Override
	public SoftwareRelease registerSoftwareRelease(String softwareReleaseUrl) throws Exception {
		//TODO Correct exception
		if (computerGuid == null) {
			throw new Exception("Computer has not been registered. Please use registerComputer before.");
		}
		return new SoftwareRelease(softwareReleaseUrl, computerGuid);
	}

	public ComputerPartition registerComputerPartition(String computerGuid, String partitionId) {
		String jsonobj = slaposMasterRestClient.get("/" + computerGuid + "/partition/" + partitionId);
		ObjectMapper mapper = new ObjectMapper();
		ComputerPartition computerPartition = null;
		try {
			computerPartition = mapper.readValue(jsonobj, ComputerPartition.class);
		} catch (JsonParseException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (JsonMappingException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return computerPartition;
	}

	@Override
	public OpenOrder registerOpenOrder() {
		return new OpenOrder(getConnectionWrapper());
	}

	@Override
	public Supply registerSupply() {
		return new Supply(getConnectionWrapper());
	}

	public ClientWrapper getConnectionWrapper() {
		return slaposMasterRestClient;
	}
}
