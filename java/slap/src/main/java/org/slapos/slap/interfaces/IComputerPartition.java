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

import java.util.Map;


/**
 * Computer Partition interface specification
 * public interfacees which implement IComputerPartition can propagate the computer
 * partition state to the SLAPGRID server and request new computer partition
 * creation.
 */
public interface IComputerPartition extends IBuildoutController {

	/**
	 * Request software release instanciation to slapgrid server.
	 * 
	 * Returns a new computer partition document, where this sofware release will
	 * be installed.
	 * 
	 * software_release -- uri of the software release
	 *                     which has to be instanciated
	 * 
	 * software_type -- type of component provided by software_release
	 * 
	 * partition_reference -- local reference of the instance used by the recipe
	 *                        to identify the instances.
	 * 
	 * shared -- boolean to use a shared service
	 * 
	 * partition_parameter_kw -- dictionary of parameter used to fill the
	 *                           parameter dict of newly created partition.
	 * 
	 * filter_kw -- dictionary of filtering parameter to select the requested
	 *              computer partition.
	 * 
	 *   computer_reference - computer of the requested partition
	 *   partition_type - virtio, slave, full, limited
	 *   port - port provided by the requested partition
	 * 
	 * Example:
	 *    request('http://example.com/toto/titi', 'mysql_1')
	 */
	public IComputerPartition request(String softwareRelease, String softwareType,
			String partitionReference, 
			boolean shared, // = false
			Map<String, Object> partitionParameter, // = null
			Map<String, String> filter); // = null

	/**
	 * Notify (to the slapgrid server) that the software instance is 
	 * available and stopped.
	 */
	public void stopped();

	/**
	 * Notify (to the slapgrid server) that the software instance is 
	 * available and started.
	 */
	public void started();

	/**
	 * Returns a string representing the identifier of the computer partition
	 * inside the slapgrid server.
	 */
	public String getId();

	/**
	 * Returns a string representing the expected state of the computer partition.
	 * The result can be: started, stopped, destroyed
	 */
	public String getState();

	/**
	 * Returns the software release associate to the computer partition.
	 * Raise an INotFoundError if no software release is associated.
	 */
	public String getSoftwareRelease();

	/**
	 * Returns a dictionary of instance parameters.
	 * 
	 * The contained values can be used to fill the software instanciation
	 * profile.
	 */
	public Map<String, String> getInstanceParameterDict();

	/**
	 * Set instance parameter informations on the slagrid server.
	 * 
	 * partition_parameter_kw -- dictionary of parameters.
	 * 
	 * This method can be used to propagate connection informations (like
	 * service's port).
	 */
	public void setInstanceParameterDict(Map<String, String> partition_parameter_kw);

	/**
	 * Associate a usage log to the computer partition.
	 * This method does not report the usage to the slapgrid server. See
	 * IComputer.report.
	 * 
	 * usage_log -- a text describing the computer partition usage.
	 *              It can be an XML for example.
	 */
	public void setUsage(String usage_log);
}
