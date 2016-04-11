# XXX For now, this script requires proxy manager

# base_category_list : list of category values we need to retrieve
# user_name : string obtained from getSecurityManager().getUser().getUserName() [NuxUserGroup]
#             or from getSecurityManager().getUser().getId() [PluggableAuthService with ERP5GroupManager]
# object : object which we want to assign roles to.
# portal_type : portal type of object

# must always return a list of dicts

if obj is None:
  return []

portal = obj.getPortalObject()
computer = obj

category_list = []

scope = computer.getAllocationScope()
if scope == 'open/public':
  return {"Auditor": ["R-SHADOW-PERSON"]}
elif scope == 'open/personal':
  person = computer.getSourceAdministrationValue(portal_type="Person")
  if person is not None:
    return {"Auditor": ["SHADOW-%s" % person.getReference()]}
elif scope == 'open/friend':
  person_list = computer.getDestinationSectionValueList(portal_type="Person")
  if person_list:
    return {"Auditor": ["SHADOW-%s" % x.getReference() for x in person_list]}

return category_list
