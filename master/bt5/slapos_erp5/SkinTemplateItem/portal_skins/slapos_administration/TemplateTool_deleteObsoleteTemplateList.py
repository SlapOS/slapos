"""
  This is a custom version, because we don't want to definitly delete the objects
  but only change state to 'deleted'.
  
  This script can also include custom deletions, which comes from legacy 
  implementations and/or garbage left behind from upgrader.
"""

from Products.CMFActivity.ActiveResult import ActiveResult
portal = context.getPortalObject()
active_process = portal.restrictedTraverse(active_process)


portal_templates = context.getPortalObject().portal_templates
delete_list = []
bt_list = portal_templates.objectValues()
for bt in bt_list:
  bt_id = bt.getId()
  installation_state = bt.getInstallationState()
  if installation_state in ('replaced'):
    if fixit:
      bt.getObject().delete()
      summary="%s was deleted." % bt.getRelativeUrl()
    else:
      summary="%s is going to be deleted." % bt.getRelativeUrl()
    active_process.postResult(ActiveResult(
         summary=summary,
         severity=2,
         detail=""))

  elif installation_state == 'not_installed':
    title = bt.getTitle()
    modification_date = bt.getModificationDate()
    for x in bt_list:
      if (x.getTitle() == title and
          x.getInstallationState() in ('installed', 'not_installed') and
          x.getModificationDate() > modification_date):
        if fixit:
          bt.getObject().delete()
          summary="%s was deleted." % bt.getRelativeUrl()
        else:
          summary="%s is going to be deleted." % bt.getRelativeUrl()
        active_process.postResult(ActiveResult(
             summary=summary,
             severity=2,
             detail=""))
        break

  elif bt.getTitle().startswith("vifib_") and bt.getVersion() == "999": 
    delete_list.append(bt_id)

if len(delete_list):
  if fixit:
    context.portal_templates.manage_delObjects(delete_list)
    summary="The bt5 with the followed ids were deleted forever: %s" % delete_list
  else:
    summary="The bt5 with the followed ids are going to be deleted forever: %s" % delete_list
  active_process.postResult(ActiveResult(
     summary=summary,
     severity=2,
     detail=""))
