from Products.Formulator.Errors import ValidationError, FormValidationError
form = getattr(context,form_id)
person = context.ERP5Site_getAuthenticatedMemberPersonValue()

# Call Base_edit
result, result_type = person.Base_edit(form_id, silent_mode=1, field_prefix='your_')

# Return if not appropriate
if result_type != 'edit':
  return result

kw, encapsulated_editor_list = result

# Update basic attributes
person.edit(REQUEST=context.REQUEST, edit_order=form.edit_order, **kw)
for encapsulated_editor in encapsulated_editor_list:
  encapsulated_editor.edit(person)

#Redirect the user
message = context.Base_translateString("Your personnal information has been updated")
context.Base_redirect(form_id,keep_items={'portal_status_message':message})
