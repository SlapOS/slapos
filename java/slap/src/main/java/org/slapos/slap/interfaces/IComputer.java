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

import java.util.ArrayList;


/**
 * Computer interface specification
 * 
 * public interfacees which implement IComputer can fetch informations from the slapgrid
 * server to know which Software Releases and Software Instances have to be
 * installed.
 */
public interface IComputer {

	/**
	 * Returns the list of software release which has to be supplied by the
	 * computer.
	 * 
	 * Raise an INotFoundError if computer_guid doesn't exist.
	 */
	public ArrayList<String> getSoftwareReleaseList();

	/**
	 * Returns the list of configured computer partitions associated to this
	 * computer.
	 * 
	 * Raise an INotFoundError if computer_guid doesn't exist.
	 */
	public ArrayList<IComputerPartition> getComputerPartitionList();

	/**
	 * Report the computer usage to the slapgrid server. 
	 * IComputerPartition.setUsage has to be called on each computer partition to
	 * public functionine each usage.
	 * 
	 * computer_partition_list -- a list of computer partition for which the usage
	 *                            needs to be reported.
	 */
	public void reportUsage(String[] computer_partition_list);
}