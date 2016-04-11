"""
  Unindexed deleted business template in order to the manager don't see it.
  
  This is script is probably a workarround.
"""

from Products.CMFActivity.ActiveResult import ActiveResult
portal = context.getPortalObject()
active_process = portal.restrictedTraverse(active_process)

unindexed_list = []
for i in context.portal_templates.portal_catalog(portal_type="Business Template"):
  if i.getInstallationState() == "deleted":
    unindexed_list.append(i.path)
    if fixit:
      context.portal_catalog.activate(
        activity="SQLQueue").unindexObject(uid=i.uid)

if len(unindexed_list):
  if fixit:
    summary="The followed bt5 were unindexed: %s" % unindexed_list
  else:
    summary="The followed bt5 are going to be unindexed: %s" % unindexed_list
  active_process.postResult(ActiveResult(
     summary=summary,
     severity=2,
     detail=""))
