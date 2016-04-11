from Products.DCWorkflow.DCWorkflow import ValidationFailed
from Products.ZSQLCatalog.SQLCatalog import SimpleQuery, ComplexQuery
from zExceptions import Unauthorized

if context.getPortalType() not in ('Software Instance', 'Slave Instance'):
  raise TypeError('%s is not supported' % context.getPortalType())

def markHistory(document, comment):
  portal_workflow = document.portal_workflow
  last_workflow_item = portal_workflow.getInfoFor(ob=document,
                                          name='comment', wf_id='edit_workflow')
  if last_workflow_item != comment:
    portal_workflow.doActionFor(document, action='edit_action', comment=comment)

def assignComputerPartition(software_instance, hosting_subscription):
  computer_partition = software_instance.getAggregateValue(
      portal_type="Computer Partition")
  if computer_partition is None:
    hosting_subscription = software_instance.getSpecialiseValue(
        portal_type='Hosting Subscription')
    person = hosting_subscription.getDestinationSectionValue(portal_type='Person')
    if person is None:
      raise ValueError('%s does not have person related' % hosting_subscription.getRelativeUrl())
    if not person.Person_isAllowedToAllocate():
      raise Unauthorized('Allocation disallowed')

    tag = None
    try:
      sla_dict = software_instance.getSlaXmlAsDict()
    except Exception:
      # Note: it is impossible to import module exceptions from python scripts
      computer_partition_relative_url = None
    else:

      # "Each instance should be allocated to a different network." (i.e at most one instance of the tree per network)
      computer_network_query = None
      if sla_dict.get('mode', None) == 'unique_by_network':
        # Prevent creating two instances in the same computer_network
        hosting_subscription_uid = hosting_subscription.getUid()
        tag = "%s_inProgress" % hosting_subscription_uid
        if (context.getPortalObject().portal_activities.countMessageWithTag(tag) > 0):
          # The software instance is already under creation but can not be fetched from catalog
          # As it is not possible to fetch informations, just ignore
          markHistory(software_instance,
              'Allocation failed: blocking activites in progress for %s' % hosting_subscription_uid)

        sla_dict.pop('mode')
        # XXX: does NOT scale if hosting subscription contains many SoftwareInstance
        hosting_subscription = software_instance.getSpecialiseValue()
        software_instance_tree_list = [sql_obj.getObject() \
            for sql_obj in context.getPortalObject().portal_catalog(
                portal_type=['Software Instance', 'Slave Instance'],
                default_specialise_uid=hosting_subscription.getUid(),
            )
        ]
        computer_network_query_list = []
        # Don't deploy in computer with no network
        computer_network_query_list.append(ComplexQuery(
            SimpleQuery(
            default_subordination_uid=''),
            logical_operator='not',
        ))
        for other_software_instance in software_instance_tree_list:
          computer_partition = other_software_instance.getAggregateValue()
          if not computer_partition:
            continue
          computer_network = computer_partition.getParentValue().getSubordinationValue()
          if computer_network:
            computer_network_query_list.append(ComplexQuery(
                SimpleQuery(
                default_subordination_uid=computer_network.getUid()),
                logical_operator='not',
            ))
      
        computer_network_query = ComplexQuery(*computer_network_query_list)
        hosting_subscription.serialize()

      elif sla_dict.get('mode'):
        computer_network_query = '-1'

      computer_partition_relative_url = person.Person_restrictMethodAsShadowUser(
        shadow_document=person,
        callable_object=person.Person_findPartition,
        argument_list=[software_instance.getUrlString(), software_instance.getSourceReference(),
        software_instance.getPortalType(), sla_dict, computer_network_query])
    return computer_partition_relative_url, tag

software_instance = context
if software_instance.getValidationState() != 'validated' \
  or software_instance.getSlapState() not in ('start_requested', 'stop_requested') \
  or software_instance.getAggregateValue(portal_type='Computer Partition') is not None:
  return

hosting_subscription = software_instance.getSpecialiseValue()
try:
  computer_partition_url, tag = assignComputerPartition(software_instance,
      hosting_subscription)

  # XXX: We create a dummy activity to prevent to allocations on the same network
  if tag:
    hosting_subscription.activate(activity="SQLQueue", tag=tag,
        after_tag="allocate_%s" % computer_partition_url).getId()
  
except ValueError:
  # It was not possible to find free Computer Partition
  markHistory(software_instance, 'Allocation failed: no free Computer Partition')
except Unauthorized, e:
  # user has bad balance
  markHistory(software_instance, 'Allocation failed: %s' % e)
except NotImplementedError, e:
  # user has bad balance
  markHistory(software_instance, 'Allocation failed: %s' % e)
else:
  if computer_partition_url is not None:
    try:
      software_instance.Base_checkConsistency()
    except ValidationFailed:
      # order not ready yet
      markHistory(software_instance, 'Allocation failed: consistency failed')
    else:
      software_instance.allocatePartition(computer_partition_url=computer_partition_url)
