from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized
context.setStartDate(start_date)
