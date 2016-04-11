active_process = context.newActiveProcess().getRelativeUrl()

context.portal_templates.TemplateTool_deleteObsoleteTemplateList(
  fixit=fixit, tag=tag, active_process=active_process)
  
context.portal_templates.TemplateTool_unindexDeletedObjectList(
  fixit=fixit, tag=tag, active_process=active_process)
