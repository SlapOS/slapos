base_url = 'https://monitor.app.officejs.com/#/?page=ojsm_dispatch&query=portal_type:"Software Instance" AND '

if context.getPortalType() == "Organisation":
  computer_reference = ",".join([ '"' + i.getReference() + '"' for i in context.Organisation_getComputerTrackingList()])
  return context.REQUEST.RESPONSE.redirect(base_url + "aggregate_reference:(%s)" % computer_reference)

if context.getPortalType() == "Project":
  computer_reference = ",".join([ '"' + i.getReference() + '"' for i in context.Project_getComputerTrackingList()])
  return context.REQUEST.RESPONSE.redirect(base_url + "aggregate_reference:(%s)" % computer_reference)
