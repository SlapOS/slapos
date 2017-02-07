from Products.CMFActivity.ActiveResult import ActiveResult

portal = context.getPortalObject()
reference = context.getReference()

active_process = portal.restrictedTraverse(active_process)

result = portal.portal_catalog(portal_type=context.getPortalType(),
                               reference=reference,
                               limit=2)
if len(result) != 1:
  active_process.postResult(ActiveResult(
         summary="%s %s has duplication" % (context.getRelativeUrl(), context.getReference()),
         severity=100,
         detail=""))
