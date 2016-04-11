""" 
  Add resource to current (or to be created shopping cart). 
"""
selection = context.getPortalObject().portal_selections.getSelectionFor('vifib_session_id')
if selection is None:
  context.getPortalObject().portal_selections.setSelectionParamsFor('vifib_session_id', {})
  selection = context.getPortalObject().portal_selections.getSelectionFor('vifib_session_id')
return selection

from DateTime import DateTime
from random import choice
import string

request = context.REQUEST
expire_timeout_days = 90
session_id = request.get('vifib_session_id', None)
portal_sessions = context.portal_sessions

if session_id is None:
  raise NotImplementedError, "no session..."
  ## first call so generate session_id and send back via cookie
  now = DateTime()
  session_id = ''.join([choice(string.letters) for i in range(20)])
  request.RESPONSE.setCookie('vifib_session_id', session_id, expires=(now +expire_timeout_days).fCommon(), path='/')

return portal_sessions[session_id]
