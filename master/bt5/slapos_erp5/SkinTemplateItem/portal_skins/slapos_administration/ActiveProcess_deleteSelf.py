from zExceptions import Unauthorized
if REQUEST is not None:
  raise Unauthorized

if context.getPortalType() != 'Active Process':
  raise TypeError('Call me on Active Process')

context.getParentValue().deleteContent(context.getId())
