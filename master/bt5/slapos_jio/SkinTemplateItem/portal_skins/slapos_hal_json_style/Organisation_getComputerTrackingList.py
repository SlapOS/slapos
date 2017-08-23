# This script might not be efficient to a large quantities of
# Computers

kw = {"node_uid": context.getUid()}

return [ i.getObject()
         for i in context.portal_simulation.getCurrentTrackingList(**kw)]
