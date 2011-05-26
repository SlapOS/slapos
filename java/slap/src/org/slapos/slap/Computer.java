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

import java.util.ArrayList;

import org.slapos.slap.interfaces.IComputer;
import org.slapos.slap.interfaces.IComputerPartition;

public class Computer extends SlapDocument implements IComputer {
	private String computerId;
	private ArrayList<String> softwareReleaseList;
	private ArrayList<ComputerPartition> computerPartitionList;
	private ClientWrapper connection;

	public Computer(ClientWrapper connection, String computerId) {
		this.computerId = computerId;
		this.connection = connection;
	}

	/**
	 * Synchronize computer object with server information
	 */
	private void syncComputerInformation() {
		/*	 def _syncComputerInformation(func):
	   def decorated(self, *args, **kw):
	     computer = self._connection_helper.getComputerInformation(self._computer_id)
	     for key, value in computer.__dict__.items():
	       if isinstance(value, unicode):
	         # convert unicode to utf-8
	         setattr(self, key, value.encode('utf-8'))
	       else:
	         setattr(self, key, value)
	     return func(self, *args, **kw)
	   return decorated */
	}

	/**
	 * Returns the list of software release which has to be supplied by the
	 * computer.
	 *  Raise an INotFoundError if computer_guid doesn't exist.
	 */
	public ArrayList<String> getSoftwareReleaseList() {
		syncComputerInformation();
		return this.softwareReleaseList;
	}

	public ArrayList<IComputerPartition> getComputerPartitionList() {
		syncComputerInformation();
		ArrayList<IComputerPartition> partitionToModifyList = new ArrayList<IComputerPartition>();
		for (ComputerPartition partition : computerPartitionList) {
			if (partition.need_modification) {
				partitionToModifyList.add(partition);
			}
		}
		return partitionToModifyList;
	}

	public void reportUsage(ArrayList<ComputerPartition> computer_partition_list) {
		//FIXME implement this method
		/*    if computer_partition_list == []:
      return;
    computer = Computer(self._computer_id);
    computer.computer_partition_usage_list = computer_partition_list;
    marshalled_slap_usage = xml_marshaller.dumps(computer);
    self._connection_helper.POST('/useComputer', {
      'computer_id': self._computer_id,
      'use_string': marshalled_slap_usage});
		 */
	}

	public void updateConfiguration(String xml) {/*
    self.connectionHelper.POST(
        "/loadComputerConfigurationFromXML", { "xml" : xml });
    return this.connectionHelper.response.read();*/
	}

	@Override
	public void reportUsage(String[] computer_partition_list) {
		// FIXME Not implemented

	}
}