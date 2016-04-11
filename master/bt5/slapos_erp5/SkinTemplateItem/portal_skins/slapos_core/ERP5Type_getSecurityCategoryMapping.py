"""
Core security script - defines the way to get security groups of the current user.

WARNING: providing such script in erp5_dms could be dangerous
if this conflicts with an existing production site which uses
deprecated ERP5Type_asSecurityGroupIdList
"""

return (
  # Person security
  ('ERP5Type_getSecurityCategoryFromAssignment', ['group']),
  ('ERP5Type_getSecurityCategoryFromAssignment', ['role']),

  # Computer security
  ('ERP5Type_getComputerSecurityCategory', ['role']),

  # Instance security
  ('ERP5Type_getSoftwareInstanceSecurityCategory', ['role']),
  ('ERP5Type_getSoftwareInstanceSecurityCategory', ['aggregate']),

)
