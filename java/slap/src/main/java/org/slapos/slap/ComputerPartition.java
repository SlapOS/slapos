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
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import org.codehaus.jackson.JsonParseException;
import org.codehaus.jackson.map.JsonMappingException;
import org.codehaus.jackson.map.ObjectMapper;
import org.slapos.slap.exception.NotFoundException;
import org.slapos.slap.interfaces.IComputerPartition;


/*def _syncComputerPartitionInformation(func):
  """
  Synchronize computer partition object with server information
  """
  def decorated(self, *args, **kw):
    computer = self._connection_helper.getComputerInformation(self._computer_id)
    found_computer_partition = None
    for computer_partition in computer._computer_partition_list:
      if computer_partition.getId() == self.getId():
        found_computer_partition = computer_partition
        break
    if found_computer_partition is None:
      raise NotFoundError("No software release information for partition %s" %
          self.getId())
    else:
      for key, value in found_computer_partition.__dict__.items():
        if isinstance(value, unicode):
          # convert unicode to utf-8
          setattr(self, key, value.encode('utf-8'))
        if isinstance(value, dict):
          new_dict = {}
          for ink, inv in value.iteritems():
            if isinstance(inv, (list, tuple)):
              new_inv = []
              for elt in inv:
                if isinstance(elt, (list, tuple)):
                  new_inv.append([x.encode('utf-8') for x in elt])
                else:
                  new_inv.append(elt.encode('utf-8'))
              new_dict[ink.encode('utf-8')] = new_inv
            elif inv is None:
              new_dict[ink.encode('utf-8')] = None
            else:
              new_dict[ink.encode('utf-8')] = inv.encode('utf-8')
          setattr(self, key, new_dict)
        else:
          setattr(self, key, value)
    return func(self, *args, **kw)
  return decorated
 */

// FIXME beware! I am not respecting Java conventions, but be aware that JSON is unmarshalled to instance of this crap. If you change those attributes, please consider also changing the slapos protocol.
public class ComputerPartition extends SlapDocument implements IComputerPartition {
	private String computer_id;
	private String computer_partition_id; // Id is internal representation of instance in slapos
	private String partition_reference; // reference is human chosen name for the instance
	//TODO enum for requestedState, not string.
	private String requested_state;
	//TODO private, getters/setters
	public Map<String, Object> parameter_dict;
	public boolean need_modification;
	public Map<String, Object> connection_dict;
	public String software_release;
	private String software_type;
	private boolean shared;
	private Map<String, String> filter;
	private ClientWrapper connection;

	public ComputerPartition(String computerId, String partitionId) {
		this.computer_id = computerId;
		this.computer_partition_id = partitionId;
	}
	
	public ComputerPartition(ClientWrapper connection) {
		this.connection = connection;
	}

	//FIXME @_syncComputerPartitionInformation
	public ComputerPartition request(String softwareRelease, String softwareType, String partitionReference,
			boolean shared, Map<String, Object> partitionParameter, Map<String, String> filter) {
		//shared=False, filter_kw=None
		if (partitionParameter == null) {
			partitionParameter = new HashMap<String, Object>();
		}
		if (filter == null) {
			filter = new HashMap<String, String>();
		}
		ComputerPartition cp = new ComputerPartition(computer_id, computer_partition_id);
		cp.setSoftware_release(softwareRelease);
		cp.setSoftware_type(softwareType);
		cp.setPartition_reference(partitionReference);
		cp.setShared(shared);
		cp.setParameter_dict(partitionParameter);
		cp.setFilter(filter);

		// Sends it, reads response
		return sendRequest(cp);
	}

	/**
	 * This methods is used as a helper for ComputerPartition.request and OpenOrder.request. Those 2 methods prepare the parameterList, while this one actually sends the request to server
	 * @param parameterList
	 * @return
	 */
	public ComputerPartition sendRequest(ComputerPartition cp) {
		// Converts computer partition to Json

		String parameterJson = ClientWrapper.object2Json(cp, "ComputerPartition");

		// Sends it, reads response
		ComputerPartition computerPartition = null;
		try {
			String responseJson = connection.post("/partition", parameterJson);
			ObjectMapper mapper = new ObjectMapper();
			//FIXME change slap protocol to receive something that looks like a ComputerPartition, so that we can unmarshal it automatically
			//FIXME in the python slap library, only slap_computer_id and slap_computer_partition_id are used. What about the other parameter received?
			Map<String, Object> softwareInstance = mapper.readValue(responseJson, Map.class);
			computerPartition = new ComputerPartition(
					//TODO : check encoding.
					(String) softwareInstance.get("slap_computer_id"),
					(String) softwareInstance.get("slap_computer_partition_id"));
			computerPartition.setPartition_reference((String) softwareInstance.get("partition_reference"));
			//FIXME connection_xml is deprecated, and is a string. We need to stabilize slap code in slapproxy & al.
			//computerPartition.setConnection_dict((Map<String, Object>) softwareInstance.get("connection_xml"));
			computerPartition.setSoftware_release((String) softwareInstance.get("slap_software_release_url"));
			
			//TODO Requested State
		} catch (JsonParseException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (JsonMappingException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}

		return computerPartition;
	}
	
	/**
	 * Synchronizing computer partition informations with server. Currently, it is ugly and not network efficient. PoC.
	 */
	private void SyncComputerPartitionInformation() {
		// Fetches informations
		String responseJson = connection.get("/" + this.computer_id);
		ObjectMapper mapper = new ObjectMapper();
		// Take our computer partition, replace this.blabla with what we find
		try {
			Map<String, Object> computer = mapper.readValue(responseJson, Map.class);
			ArrayList<Map<String, Object>> computerPartitionList = (ArrayList<Map<String, Object>>) computer.get("computer_partition_list");
			for (Map<String, Object> computerPartition : computerPartitionList) {
				String partitionReference = (String) computerPartition.get("partition_reference");
				String partitionId = (String) computerPartition.get("reference");
				if (partitionReference.equalsIgnoreCase(this.getPartition_reference())) {
					System.out.println(getPartition_reference() + " synchronized with server.");
					this.setParameter_dict((Map<String, Object>) computerPartition.get("parameter_dict"));
					this.setConnection_dict((Map<String, Object>) computerPartition.get("connection_dict"));
					this.setSoftware_release((String) computerPartition.get("software_release"));
					break;
				}
			}
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
	}






	/***************
	 * Some getters/setters
	 ***************/




	public String getId() {
		return this.computer_partition_id;
	}

	//FIXME @_syncComputerPartitionInformation
	public String getState() {
		return this.requested_state;
	}

	public void setState(String state) {
		this.requested_state = state;
	}

	@Override
	public String getSoftwareRelease() {
		return this.software_release;
	}
	
	//FIXME @_syncComputerPartitionInformation
	public String getConnectionParameter(String key) throws Exception {
		SyncComputerPartitionInformation();
		if (connection_dict == null) {
			throw new Exception("Connection Dict has not been initialized.");
		}
		if (connection_dict.containsKey(key)) {
			//FIXME always string?
			return (String) connection_dict.get(key);
		}
		throw new NotFoundException(key + " not found");
	}

	public String getComputer_id() {
		return computer_id;
	}

	public void setComputer_id(String computer_id) {
		this.computer_id = computer_id;
	}

	public String getComputer_partition_id() {
		return computer_partition_id;
	}

	public void setComputer_partition_id(String computer_partition_id) {
		this.computer_partition_id = computer_partition_id;
	}

	public String getPartition_reference() {
		return partition_reference;
	}

	public void setPartition_reference(String partition_reference) {
		this.partition_reference = partition_reference;
	}

	public String getRequested_state() {
		return requested_state;
	}

	public void setRequested_state(String requested_state) {
		this.requested_state = requested_state;
	}

	public Map<String, Object> getParameter_dict() {
		return parameter_dict;
	}

	public void setParameter_dict(Map<String, Object> parameter_dict) {
		this.parameter_dict = parameter_dict;
	}

	public boolean isNeed_modification() {
		return need_modification;
	}

	public void setNeed_modification(boolean need_modification) {
		this.need_modification = need_modification;
	}

	public boolean getShared() {
		return shared;
	}

	public void setShared(boolean shared) {
		this.shared = shared;
	}

	public Map<String, Object> getConnection_dict() {
		return connection_dict;
	}

	public void setConnection_dict(Map<String, Object> connection_dict) {
		this.connection_dict = connection_dict;
	}

	public String getSoftware_release() {
		return software_release;
	}

	public void setSoftware_release(String software_release) {
		this.software_release = software_release;
	}

	public String getSoftware_type() {
		return software_type;
	}

	public void setSoftware_type(String slap_software_type) {
		this.software_type = slap_software_type;
	}

	public Map<String, String> getFilter() {
		return filter;
	}

	public void setFilter(Map<String, String> filter) {
		this.filter = filter;
	}

	@Override
	public void available() {
		// TODO Auto-generated method stub

	}

	@Override
	public void building() {
		// TODO Auto-generated method stub

	}

	@Override
	public void error(String error_log) {
		// TODO Auto-generated method stub

	}

	@Override
	public void stopped() {
		// TODO Auto-generated method stub

	}

	@Override
	public void started() {
		// TODO Auto-generated method stub

	}

	@Override
	public void setUsage(String usage_log) {
		// TODO Auto-generated method stub

	}

	@Override
	public Map<String, String> getInstanceParameterDict() {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	@Deprecated
	public void setInstanceParameterDict(
			Map<String, String> partition_parameter_kw) {
		// TODO Auto-generated method stub

	}

}