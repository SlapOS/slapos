if REQUEST is None:
  REQUEST = context.REQUEST
if response is None:
  response = REQUEST.RESPONSE

default_web_page = context
web_section = REQUEST.get("current_web_section")

return default_web_page.WebPage_viewAsWeb()
