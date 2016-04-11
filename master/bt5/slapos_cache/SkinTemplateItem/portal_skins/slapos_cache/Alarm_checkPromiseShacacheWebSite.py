from Products.CMFActivity.ActiveResult import ActiveResult

portal = context.getPortalObject()
web_site_module = getattr(portal, 'web_site_module', None)
if web_site_module is None:
  # web_site_module is not present yet, so it is impossible
  # to keep the promise
  return False

shacache = getattr(web_site_module, 'shacache', None)
shadir = getattr(web_site_module, 'shadir', None)

expected_state = context.portal_preferences.getPreferredShacacheWebsiteExpectedState("published")

active_result = ActiveResult()
if expected_state == "published" and shacache is None:
  severity = 1
  summary = "Shacache WebSite do not exist"
  detail = ""
elif expected_state == "published" and shadir is None:
  severity = 1
  summary = "Shadir WebSite do not exist"
  detail = ""
elif expected_state == "published" and shacache.getSkinSelectionName() != "SHACACHE":
  severity = 1
  summary = "shacache site don't have SHACACHE as skin selection name"
  detail = ""
elif expected_state == "published" and shadir.getSkinSelectionName() != "SHADIR":
  severity = 1
  summary = "shadir site don't have SHADIR as skin selection name"
  detail = ""
elif shacache is not None and shacache.getValidationState() != expected_state:
  severity = 1
  summary = "shacache site is not what is expected: %s" % expected_state
  detail = ""
elif shadir is not None and shadir.getValidationState() != expected_state:
  severity = 1
  summary = "shadir site is not published %s" % expected_state
  detail = ""
else:
  severity = 0
  summary = "Nothing to do."
  detail = ""

active_result.edit(
  summary=summary, 
  severity=severity,
  detail=detail)

context.newActiveProcess().postResult(active_result)
