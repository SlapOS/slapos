from DateTime import DateTime
import json
portal = context.getPortalObject()
from Products.ERP5Type.Document import newTempDocument

public_category_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/public", None).getUid()

friend_category_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/friend", None).getUid()

personal_category_uid = portal.restrictedTraverse(
  "portal_categories/allocation_scope/open/personal", None).getUid()

l = []

show_all = False
if "show_all" in kw:
  show_all = kw.pop("omit_zero_ticket")


memcached_dict = context.getPortalObject().portal_memcached.getMemcachedDict(
  key_prefix='slap_tool',
  plugin_path='portal_memcached/default_memcached_plugin')

def checkForError(reference):
  try:
    d = memcached_dict[reference]
  except KeyError:
    return 1

  d = json.loads(d)
  result = d['text']
  #last_contact = DateTime(d.get('created_at'))

  # Optimise by checking memcache information first.
  if result.startswith('#error '):
    return 1



for computer in portal.portal_catalog(
  default_allocation_scope_uid = [personal_category_uid, public_category_uid, friend_category_uid],
  select_list="reference",
  **kw):

  uid_list = [computer.getUid()]
  computer_partition_uid_list = [cp.uid for cp in computer.searchFolder(portal_type="Computer Partition")]

  instance_count = 0
  instance_error_count = 0
  if computer_partition_uid_list:
    for instance in portal.portal_catalog(
      portal_type="Software Instance",
      select_list="specialise_uid, reference",
      default_aggregate_uid=computer_partition_uid_list):
        instance_count += 1
        if instance.specialise_uid is not None:
          uid_list.append(instance.specialise_uid or computer.getUid())
        if checkForError(instance.reference) is not None:
          instance_error_count += 1
          

  related_ticket_quantity = portal.portal_catalog.countResults(
                                portal_type='Support Request',
                                simulation_state=["validated", "suspended"],
                                default_aggregate_uid=uid_list)[0][0]


  if show_all or related_ticket_quantity > 0:
    partition_use_ratio = float(instance_count)/len(computer_partition_uid_list)
    instance_error_ratio = float(instance_error_count)/instance_count

    l.append(
       newTempDocument(context, '%s'% computer.id, **{"title": computer.title,
                                                 "uid": "%s_%s" % (computer.getUid(), instance_count),
                                                 "reference": computer.reference,
                                                 "partition_use_ratio": partition_use_ratio,
                                                 "partition_use_percentage": "%.2f%%" % (partition_use_ratio*100),
                                                 "capacity_scope": computer.getCapacityScopeTitle(),
                                                 "instance_error_ratio": instance_error_ratio,
                                                 "instance_error_percentage": "%.2f%%" %  (instance_error_ratio*100),
                                                 "instance_quantity": instance_count,
                                                 "instance_error_quantity": instance_error_count,
                                                 "partition_quantity": len(computer_partition_uid_list),
                                                 "ticket_quantity": related_ticket_quantity }))

l.sort(key=lambda obj: obj.instance_error_ratio, reverse=True)

return l
