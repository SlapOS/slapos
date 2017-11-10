size = 0
for ds in context.objectValues():
  size += ds.getSize()
return size
