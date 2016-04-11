from Products.ERP5Type.DateUtils import addToDate
from DateTime import DateTime
from Products.ZSQLCatalog.SQLCatalog import Query

portal = context.getPortalObject()

for key in ['portal_type', 'sort_on']:
  if key in query_kw:
    query_kw.pop(key)
#if not 'limit' in query_kw:
#  query_kw['limit'] = 31 # limit is for one month by default
if grouping_reference is not None:
  query_kw['grouping_reference'] = grouping_reference

  sale_packing_list = portal.portal_catalog.getResultValue(
    portal_type='Sale Packing List',
    reference=grouping_reference,
    )
  if not sale_packing_list: # Strange cannot find this packing list ?
    return []
  min_date = sale_packing_list.getStopDate()
  min_date = addToDate(min_date, dict(day=-31)) # Get max 31 (one accounting period) latest published consumption lines
  
  query_kw['movement.start_date'] = Query(range="min",
      **{'movement.start_date': min_date})

cpu_resource_uid = context.service_module.cpu_load_percent.getUid()
memory_resource_uid = context.service_module.memory_used.getUid()
consumption_dict = {}

def getPackingListLineForResource(resource_uid_list):
  return portal.portal_catalog(
    portal_type="Sale Packing List Line",
    default_resource_uid = resource_uid_list,
    **query_kw
  )

def setDetailLine(packing_list_line):
  start_date = DateTime(packing_list_line.getStartDate()).strftime('%Y/%m/%d')
  hosting_reference = packing_list_line.getAggregateReference(
                                            portal_type='Hosting Subscription')
  hosting_title = packing_list_line.getAggregateTitle(
                                            portal_type='Hosting Subscription')
  software_instance = packing_list_line.getAggregateValue(
                                            portal_type='Software Instance')
  if software_instance is None:
    # In case we found SPL line not aggregated to instance and hosting
    return
  instance_reference = software_instance.getReference()
  #default_line = {'date': {'hosting_ref': ['hs_title', {'instance_ref': ['inst_title', ['res1', 'res2', 'resN'] ] } ] } }
  if not start_date in consumption_dict:
    # Add new date line
    consumption_dict[start_date] = {hosting_reference: 
                                      [hosting_title, 
                                        {instance_reference: 
                                          [software_instance.getTitle(), 
                                            [0.0, 0.0]
                                          ]
                                        }
                                      ]
                                    }
  # Add new Hosting line
  if not hosting_reference in consumption_dict[start_date]:
    consumption_dict[start_date][hosting_reference] = [hosting_title, 
                                                        {instance_reference: 
                                                          [software_instance.getTitle(), 
                                                            [0.0, 0.0]
                                                          ]
                                                        }
                                                      ]
  # Add new instance line
  if not instance_reference in consumption_dict[start_date][hosting_reference][1]:
    consumption_dict[start_date][hosting_reference][1][instance_reference] = [
        software_instance.getTitle(),  [0.0, 0.0]
      ]
  if packing_list_line.getResourceUid() == cpu_resource_uid:
    quantity = round(float(packing_list_line.getQuantity()), 3)
    consumption_dict[start_date][hosting_reference][1][instance_reference][1][0] = quantity
  elif packing_list_line.getResourceUid() == memory_resource_uid:
    quantity = round( (float(packing_list_line.getQuantity())/1024.0), 3)
    consumption_dict[start_date][hosting_reference][1][instance_reference][1][1] = quantity


# Add CPU_LOAD consumption details
for packing_list_line in getPackingListLineForResource([cpu_resource_uid,
                                                        memory_resource_uid]):
  setDetailLine(packing_list_line)

consumption_list = []
for date in sorted(consumption_dict):
  for hosting_key in sorted(consumption_dict[date]):
    hosting_title, instance_dict = consumption_dict[date][hosting_key]
    for instance_value_list in instance_dict.values():
      instance_title, values = instance_value_list
      consumption_list.append([date, hosting_title, instance_title, values[0], values[1]])

return consumption_list
