"""
  General setup actions to adjust the clone after copy and restore data from 
  clone.
"""

## Install erp5_ui_test_core and setup DummyMailHost to prevent to send emails
# Make sure repository is ok.
context.Alarm_installPromiseTemplateTool()

bt5_list = ['erp5_ui_test_core', ]

template_tool = context.getPortalObject().portal_templates
template_tool.upgradeSite(bt5_list, delete_orphaned=False, dry_run=False)

context.getPortalObject().ERP5Site_setupDummyMailHost()

# Finished to setup DummyMailHost
