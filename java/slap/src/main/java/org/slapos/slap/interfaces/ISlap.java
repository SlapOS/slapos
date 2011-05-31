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
 *****************************************************************************/

package org.slapos.slap.interfaces;

import org.slapos.slap.exception.NotFoundException;

/**
 * Note: all strings accepted/returned by the slap library are encoded in UTF-8.
 * Initialise slap connection to the slapgrid server
 * 
 * Slapgrid server URL is public functionined during the slap library
 * installation, as recipes should not use another server.
 */
public interface ISlap {

	/**
	 * Initialize the connection parameters to the slapgrid servers.
	 * 
	 * slapgrid_uri -- uri the slapgrid server connector
	 * 
	 * authentification_key -- string the authentificate the agent.
	 * 
	 * Example: https://slapos.server/slap_interface
	 */
	public void initializeConnection(String slapgridUri,
			String authentificationKey);

	/**
	 * Initialize the connection parameters to the slapgrid servers.
	 * 
	 * slapgrid_uri -- uri the slapgrid server connector
	 * 
	 * authentification_key -- string the authentificate the agent.
	 * 
	 * Example: https://slapos.server/slap_interface
	 */
	public void initializeConnection(String slapgridUri);

	/**
	 * Instanciate a computer in the slap library.
	 * 
	 * computer_guid -- the identifier of the computer inside the slapgrid
	 * server.
	 */
	public IComputer registerComputer(String computerGuid);

	/**
	 * Instanciate a computer partition in the slap library, fetching
	 * informations from master server.
	 * 
	 * @param computerGuid
	 *            -- the identifier of the computer inside the slapgrid server.
	 * 
	 * @param partitionId
	 *            -- the identifier of the computer partition inside the
	 *            slapgrid server.
	 * 
	 *            Raise a NotFoundError if computer_guid doesn't exist.
	 */
	public IComputerPartition registerComputerPartition(String computerGuid,
			String partitionId) throws NotFoundException;

	/**
	 * Instanciate a software release in the slap library.
	 * 
	 * @param softwareRelease
	 *            -- uri of the software release public functioninition
	 * @throws Exception 
	 */
	public ISoftwareRelease registerSoftwareRelease(String softwareReleaseUrl) throws Exception;

	/**
	 * Instanciate an open order in the slap library.
	 * @return 
	 */
	public IOpenOrder registerOpenOrder();

	/**
	 * Instanciate a supply in the slap library.
	 */
	public ISupply registerSupply();
}