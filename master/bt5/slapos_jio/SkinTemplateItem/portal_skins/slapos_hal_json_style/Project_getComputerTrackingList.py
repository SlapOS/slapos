# This script might not be efficient to a large quantities of
# Computers
from DateTime import DateTime

kw = {"project_uid": context.getUid(),
      "at_date": DateTime()}

return [ i.getObject()
           for i in context.portal_simulation.getCurrentTrackingList(**kw)]
