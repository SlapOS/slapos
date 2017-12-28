"""Hook called when a computer object is closed.

We want to reset reference, which is the user login in ERP5Security.
One exception is when a person object is installed from business template.
"""
if context.getPortalType() != "Organisation":
  return
context.Organisationk_init()
