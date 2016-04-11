portal = context.getPortalObject()
portal_type = 'Template Tool'
tag = 'upgrade_upgrader_%s' % random.randint(0, 2000)
method_kw = {'bt5_list':['erp5_upgrader', 'slapos_upgrader'],
             'deprecated_after_script_dict': None,
             'deprecated_reinstall_set': None,
             'dry_run': False,
             'delete_orphaned': False,
             'keep_bt5_id_set': [],
             'update_catalog': False}


portal.portal_catalog.searchAndActivate(
       portal_type=portal_type,
       method_id='upgradeSite',
       method_kw=method_kw,
       activate_kw=dict(tag=tag, priority=2))
