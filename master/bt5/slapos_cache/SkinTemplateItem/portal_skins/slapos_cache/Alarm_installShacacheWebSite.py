portal = context.getPortalObject()
shacache = getattr(portal.web_site_module, 'shacache', None)
shadir = getattr(portal.web_site_module, 'shadir', None)

expected_state = context.portal_preferences.getPreferredShacacheWebsiteExpectedState("published")

if expected_state == "published" and shacache is None:
  shacache = portal.web_site_module.newContent(id='shacache', 
                                        title="Shacache")

if expected_state == "published" and shadir is None:
  shadir = portal.web_site_module.newContent(id='shadir',
                                      title="Shadir")

if shadir is None and shacache is None:
  # Nothing to do
  return 

if expected_state == "published":
  shacache.setSkinSelectionName("SHACACHE")
  shadir.setSkinSelectionName("SHADIR")

if expected_state == "published":
  if portal.portal_workflow.isTransitionPossible(shacache, "publish"):
    shacache.publish()

  if portal.portal_workflow.isTransitionPossible(shadir, "publish"):
    shadir.publish()
  return


if portal.portal_workflow.isTransitionPossible(shacache, "embeed"):
  shacache.embeed()

if portal.portal_workflow.isTransitionPossible(shadir, "embeed"):
  shadir.embeed()
