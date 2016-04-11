from DateTime import DateTime
from Products.ZSQLCatalog.SQLCatalog import Query
from Products.ERP5Type.Document import newTempDocument

portal = context.getPortalObject()

start_date = query_kw.pop('start_date', None)
stop_date = query_kw.pop('stop_date', None)
software_instance_uid = query_kw.pop('software_instance', None)
hosting_subscription_uid = query_kw.pop('hosting_subscription_uid', None)
resource_uid = query_kw.pop('resource_service', None)
comparison_operator = query_kw.pop('resource_operator', None)
resource_value = query_kw.pop('resource_value', None)

if not software_instance_uid and not hosting_subscription_uid:
  return []

if start_date:
  query_kw['movement.start_date'] = dict(range='min', query=start_date)
if stop_date:
  query_kw['movement.stop_date'] = dict(range='ngt', 
                                     query=stop_date.latestTime())

if software_instance_uid and software_instance_uid != 'all':
  query_kw['aggregate_uid'] = software_instance_uid
elif hosting_subscription_uid and hosting_subscription_uid != 'all':
  query_kw['aggregate_uid'] = hosting_subscription_uid
elif context.getPortalType() == 'Person':
  validation_state = query_kw.pop('hosting_validation_state', None)
  hosting_uid_list = []
  for subscription in portal.portal_catalog(
                          portal_type='Hosting Subscription',
                          validation_state=validation_state,
                          default_destination_section_uid=context.getUid()):
    if validation_state == 'validated' and subscription.getSlapState() == 'destroy_requested':
      continue
    if validation_state == 'archived' and subscription.getSlapState() != 'destroy_requested':
      continue
    hosting_uid_list.append(subscription.getUid())
  if hosting_uid_list:
    query_kw['aggregate_uid'] = hosting_uid_list
  else:
    return []
elif context.getPortalType() in ['Software Instance', 'Hosting Subscription',
                                  'Computer']:
  query_kw['aggregate_uid'] = context.getUid()
else:
  return []

cpu_resource_uid = context.service_module.cpu_load_percent.getUid()
memory_resource_uid = context.service_module.memory_used.getUid()
disk_resource_uid = context.service_module.disk_used.getUid()
resource_uid_list = [cpu_resource_uid, memory_resource_uid, disk_resource_uid]
if resource_uid and comparison_operator and resource_value:
  resource_uid_list = [resource_uid]
  query_kw['quantity'] = dict(quantity=resource_value, range=comparison_operator)

consumption_dict = {}

def getPackingListLineForResource(resource_uid_list):
  return portal.portal_catalog(
    portal_type="Sale Packing List Line",
    default_resource_uid = resource_uid_list,
    **query_kw
  )

def setDetailLine(packing_list_line):
  start_date = DateTime(packing_list_line.getStartDate()).strftime('%Y/%m/%d')
  hosting_s = packing_list_line.getAggregateValue(
                                            portal_type='Hosting Subscription')
  software_instance = packing_list_line.getAggregateValue(
                                            portal_type='Software Instance')
  computer_partition = packing_list_line.getAggregateValue(
                                            portal_type='Computer Partition')
  if software_instance is None:
    # In case we found SPL line not aggregated to instance and hosting
    return
  hosting_reference = hosting_s.getReference()
  instance_reference = software_instance.getReference()
  computer_title = ""
  if computer_partition is not None:
    computer = computer_partition.getParent()
    computer_title = computer.getTitle() if computer.getCpuCore() is None else '%s (%s CPU Cores)' % (computer.getTitle(), computer.getCpuCore())
  #default_line = {'date': {'hosting_ref': ['hs_title', {'instance_ref': ['inst_title', ['res1', 'res2', 'resN'] ] } ] } }
  if not start_date in consumption_dict:
    # Add new date line
    consumption_dict[start_date] = {hosting_reference: 
                                      [hosting_s.getTitle(), 
                                        {instance_reference: 
                                          [software_instance.getTitle(), 
                                            [0.0, 0.0, 0.0],
                                            software_instance.getRelativeUrl(),
                                            computer_title
                                          ]
                                        },
                                        hosting_s.getRelativeUrl()
                                      ]
                                    }
  # Add new Hosting line
  if not hosting_reference in consumption_dict[start_date]:
    consumption_dict[start_date][hosting_reference] = [hosting_s.getTitle(),
                                                        {instance_reference: 
                                                          [software_instance.getTitle(), 
                                                            [0.0, 0.0, 0.0],
                                                            software_instance.getRelativeUrl(),
                                                            computer_title
                                                          ]
                                                        },
                                                        hosting_s.getRelativeUrl()
                                                      ]
  # Add new instance line
  if not instance_reference in consumption_dict[start_date][hosting_reference][1]:
    consumption_dict[start_date][hosting_reference][1][instance_reference] = [
        software_instance.getTitle(),  [0.0, 0.0, 0.0], software_instance.getRelativeUrl(),
        computer_title
      ]
  if packing_list_line.getResourceUid() == cpu_resource_uid:
    quantity = round(float(packing_list_line.getQuantity()), 3)
    consumption_dict[start_date][hosting_reference][1][instance_reference][1][0] = quantity
  elif packing_list_line.getResourceUid() == memory_resource_uid:
    quantity = round( float(packing_list_line.getQuantity()), 3)
    consumption_dict[start_date][hosting_reference][1][instance_reference][1][1] = quantity
  elif packing_list_line.getResourceUid() == disk_resource_uid:
    quantity = round( float(packing_list_line.getQuantity()), 3)
    consumption_dict[start_date][hosting_reference][1][instance_reference][1][2] = quantity

# Add CPU_LOAD consumption details
for packing_list_line in getPackingListLineForResource(resource_uid_list):
  setDetailLine(packing_list_line)

consumption_list = []
i = 1
# Sort on movement.start_date in catalog doesn't work !
for date in sorted(consumption_dict, reverse=True):
  for hosting_key in sorted(consumption_dict[date]):
    hosting_title, instance_dict, hs_url = consumption_dict[date][hosting_key]
    for instance_value_list in instance_dict.values():
      instance_title, values, instance_url, computer_title = instance_value_list
      line = newTempDocument(portal, instance_url, uid="%s_%s" % (context.getUid(), i))
      line.edit(
        title=hosting_title,
        start_date=date,
        instance_title=instance_title,
        cpu_load=values[0],
        memory_used=values[1],
        disk_used=values[2],
        computer_title=computer_title,
        hosting_url=hs_url,
        instance_url=instance_url
      )
      consumption_list.append(line)
      i += 1

return consumption_list
