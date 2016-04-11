kw['portal_type'] = 'Software Installation'
kw['validation_state'] = 'validated'
kw['url_string'] = context.getUrlString()

software_installation_list = context.portal_catalog(**kw)
computer_list = []
allocation_scope_list = ['open/personal', 'open/public', 'open/friend']
for software_installation in software_installation_list:
  computer = software_installation.getAggregateValue()
  if software_installation.getSlapState() == 'start_requested' and \
              computer.getAllocationScope() in allocation_scope_list:
    computer_list.append(computer)

return computer_list
