"""
  This script should returns always two list of Business Template.
   - The first list is to resolve dependencies and upgrade.
   - The second list is what you want to keep. This is useful if we want to keep
   a old business template without updating it and without removing it
"""

bt5_id_list, bt5_update_catalog_list, keep_bt5_id_list = \
  context.TemplateTool_getSlapOSMasterBusinessTemplateList()

return bt5_id_list, keep_bt5_id_list
