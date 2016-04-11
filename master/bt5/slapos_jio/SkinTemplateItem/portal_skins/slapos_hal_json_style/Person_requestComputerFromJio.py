if REQUEST.other['method'] != "POST":
  response.setStatus(405)
  return ""

person = context

person.requestComputer(computer_title=computer_title)
return context.getPortalObject().restrictedTraverse(context.REQUEST.get('computer')).Base_redirect()
