id_generator = '_generatePerDayId'
error_list = []

if context.getIdGenerator() != id_generator:
  error_list.append("%s module has incorrect ID generator" % context.getRelativeUrl())

  if fixit:
    context.setIdGenerator(id_generator)

return error_list
