from DateTime import DateTime

if context.REQUEST.get('Base_createOauth2User') is not None:
 return

context.REQUEST.set('Base_createOauth2User', 1)
portal = context.getPortalObject()

if portal.portal_activities.countMessageWithTag(tag) > 0:
  return

person = portal.ERP5Site_getAuthenticatedMemberPersonValue(reference)
if person is not None:
  return

activate_kw={'tag': tag}
person = portal.person_module.newContent(portal_type='Person',
  reference=reference,
  first_name=first_name,
  last_name=last_name,
  default_email_coordinate_text=email,
  activate_kw=activate_kw)

person.validate(activate_kw=activate_kw)

assignment_duration = portal.portal_preferences.getPreferredCredentialAssignmentDuration()
today = DateTime()
delay = today + assignment_duration

category_list = portal.portal_preferences.getPreferredSubscriptionAssignmentCategoryList()

assignment = person.newContent(
        portal_type='Assignment',
        category_list=category_list,
        start_date = today,
        stop_date = delay,
        activate_kw=activate_kw)
assignment.open(activate_kw=activate_kw)

person.setRoleList(assignment.getRoleList())
