computer = state_change['object']
portal = computer.getPortalObject()

subject_list = computer.getSubjectList()
person_list = []

for subject in subject_list:
  if subject:
    person_list.extend([x.getObject() for x in portal.portal_catalog(validation_state="validated", portal_type="Person", default_email_text=subject)])

computer.edit(destination_section_value_list=person_list)
