current_id_generator = context.getIdGenerator()

if current_id_generator != id_generator:
  if fixit:
    context.setIdGenerator(id_generator)
  return False
return True
