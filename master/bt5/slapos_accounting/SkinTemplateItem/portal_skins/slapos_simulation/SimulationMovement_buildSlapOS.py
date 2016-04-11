if context.getDelivery() is not None:
  # movement build but not indexed, so do nothing
  return

root_applied_rule = context.getRootAppliedRule()
root_applied_rule_path = root_applied_rule.getPath()

business_link = context.getCausalityValue(portal_type='Business Link')
lock_tag = 'build_in_progress_%s_%s' % (business_link.getUid(), root_applied_rule.getUid())
if context.getPortalObject().portal_activities.countMessageWithTag(lock_tag) == 0:
  business_link.build(path='%s/%%' % root_applied_rule_path, activate_kw={'tag': tag})
  root_applied_rule.activate(activity='SQLQueue', after_tag=tag, tag=lock_tag).getId()
