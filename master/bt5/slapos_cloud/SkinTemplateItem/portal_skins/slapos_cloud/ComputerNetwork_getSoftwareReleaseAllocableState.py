network = context

# XXX - The use of current authenticated person will return always 'Close' if 
#       the person is administrator (such as 'zope' user) but not the owner of computer
#       
#       person = context.ERP5Site_getAuthenticatedMemberPersonValue()
allocation_state = 'Close'
software_type = ''
filter_kw = {}

for computer in network.getSubordinationRelatedValueList():
  person = computer.getSourceAdministrationValue()
  filter_kw['computer_guid']=computer.getReference()
  try:
    isAllowed =  person.Person_restrictMethodAsShadowUser(shadow_document=person,
          callable_object=person.Person_findPartition,
          argument_list=[software_release_url, software_type, 'Software Instance',
                         filter_kw], 
          argument_dict={'test_mode': True}
    )
    if isAllowed:
      allocation_state = 'Open'
      break
  except:
    continue

return allocation_state
