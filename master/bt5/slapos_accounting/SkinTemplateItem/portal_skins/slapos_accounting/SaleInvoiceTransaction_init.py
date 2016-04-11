if kw.get('created_by_builder', 0): 
  return

context.newContent(portal_type='Sale Invoice Transaction Line',
                   id='income',)
context.newContent(portal_type='Sale Invoice Transaction Line',
                   id='receivable', )
context.newContent(portal_type='Sale Invoice Transaction Line',
                   id='collected_vat',)
