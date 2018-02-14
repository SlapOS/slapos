template_tool = context.getPortalObject().portal_templates

template_tool.updateRepositoryBusinessTemplateList(
  template_tool.getRepositoryList())

method_kw = {'bt5_list': ['erp5_core'],
             'deprecated_after_script_dict': None,
             'deprecated_reinstall_set': None,
             'dry_run': False,
             'delete_orphaned': False,
             'keep_bt5_id_set': [],
             'update_catalog': False}


template_tool.upgradeSite(**method_kw)
