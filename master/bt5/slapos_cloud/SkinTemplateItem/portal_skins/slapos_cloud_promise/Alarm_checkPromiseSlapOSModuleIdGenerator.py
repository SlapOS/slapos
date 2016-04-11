from Products.CMFActivity.ActiveResult import ActiveResult

portal = context.getPortalObject()
wrong_module_list = []
active_process = context.newActiveProcess()
for module_id in portal.objectIds(spec=('ERP5 Folder',)) + ["portal_simulation", "portal_activities"]:
  module = portal.restrictedTraverse(module_id)
  if not module.Module_assertIdGenerator('_generatePerDayId', fixit, active_process):
    wrong_module_list.append(module.getRelativeUrl())

if len(wrong_module_list) != 0:
  summary = "Some modules have incorrect ID generator"
  if fixit:
    summary += ", fixed."
    severity = 0
  else:
    severity = 1
  detail = "List: %s" % (', '.join(wrong_module_list), )
else:
  severity = 0
  summary = "Nothing to do."
  detail = ""

active_result = ActiveResult()
active_result.edit(
  summary=summary, 
  severity=severity,
  detail=detail)

active_process.postResult(active_result)
