from DateTime import DateTime
from Products.ERP5Type.Document import newTempDocument

portal = context.getPortalObject()

# Hardcode the Date Range here

today = DateTime()

date_set = set(["%s/%02d" % ((today-x).year(), (today-x).month()) for x in range(0,370, 27)])

def getSupportRequestList(creation_date, resource_uid=None):
  return portal.portal_catalog(
    portal_type="Support Request",
    default_resource_uid=resource_uid, 
    creation_date=creation_date)

def countSupportRequest(creation_date, resource_uid=None):
  return len(getSupportRequestList(creation_date, resource_uid))

def countEvent(creation_date, resource_uid=None):
  sr_uid_list = [sr.uid for sr in getSupportRequestList(creation_date, resource_uid)]
  if not sr_uid_list:
    return 0

  return portal.portal_catalog.countResults(
    default_follow_up_uid=[sr.uid for sr in getSupportRequestList(creation_date, resource_uid)],
    creation_date=creation_date)[0][0]

monitor_resource_uid = context.service_module.slapos_crm_monitoring.getUid()

stats_list = []

creation_date_list = list(date_set)
creation_date_list.sort()

for creation_date in creation_date_list:     
  line = newTempDocument(context, '%s' % creation_date.replace("/", "_"), **{
       "uid": "%s_%s" % (context.getUid(), len(stats_list)),
       "title": creation_date,
       "event_user_amount": countSupportRequest(creation_date, resource_uid='NOT %s' % monitor_resource_uid),
       "user_amount": countEvent(creation_date, resource_uid='NOT %s' % monitor_resource_uid),
       "monitor_amount": countSupportRequest(creation_date, resource_uid=monitor_resource_uid),
       "event_monitor_amount": countEvent(creation_date, resource_uid=monitor_resource_uid)})
  
  stats_list.append(line)

return stats_list
