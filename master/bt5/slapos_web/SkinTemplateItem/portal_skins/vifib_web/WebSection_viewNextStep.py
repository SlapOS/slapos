request = context.REQUEST
main_section = context.WebSite_getMainSection()

current_web_section = request.get('current_web_section', context)

if main_section == current_web_section:
  desired_index = 1
else:
  desired_index = current_web_section.getIntIndex() + 1


for section in main_section.contentValues(checked_permission="View"):
  if section.getIntIndex() == desired_index :
    next_web_section = section
    break
else: 
  next_web_section = current_web_section

keep_items = {}
if message:
  keep_items['portal_status_message'] = context.Base_translateString(message)

return next_web_section.Base_redirect('',keep_items=keep_items)
