portal = context.getPortalObject()
web_site_module = getattr(portal, 'web_site_module', None)
if web_site_module is None:
  # web_site_module is not present yet, so it is impossible
  # to keep the promise
  return False

shacache = getattr(web_site_module, 'shacache', None)
shadir = getattr(web_site_module, 'shadir', None)

expected_state = context.portal_preferences.getPreferredShacacheWebsiteExpectedState("published")
result_list = []
if expected_state == "published":
  if shacache is None:
    result_list.append("Shacache WebSite do not exist")
    if fixit:
      shacache = portal.web_site_module.newContent(id='shacache',
                                          title="Shacache")

  if shadir is None:
    result_list.append("Shadir WebSite do not exist")
    if fixit:
      shadir = portal.web_site_module.newContent(id='shadir',
                                                 title="Shadir")
  if shacache.getSkinSelectionName() != "SHACACHE":
    result_list.append("shacache site don't have SHACACHE as skin selection name")
    if fixit:
      shacache.setSkinSelectionName("SHACACHE")

  if shadir.getSkinSelectionName() != "SHADIR":
    result_list.append("shadir site don't have SHADIR as skin selection name")
    if fixit:
      shadir.setSkinSelectionName("SHADIR")

if shacache is not None and shacache.getValidationState() != expected_state:
  result_list.append("shacache site is not what is expected: %s" % expected_state)
  if fixit:
    if expected_state == "published" and \
      portal.portal_workflow.isTransitionPossible(shacache, "publish"):
      shacache.publish()
    elif expected_state == "embedded" and \
        portal.portal_workflow.isTransitionPossible(shacache, "embed"):
      shacache.embed()

if shadir is not None and shadir.getValidationState() != expected_state:
  result_list.append("shadir site is not %s" % expected_state)
  if fixit:
    if expected_state == "published" and \
      portal.portal_workflow.isTransitionPossible(shadir, "publish"):
      shadir.publish()
    elif expected_state == "embedded" and \
        portal.portal_workflow.isTransitionPossible(shadir, "embed"):
      shadir.embed()

return result_list
