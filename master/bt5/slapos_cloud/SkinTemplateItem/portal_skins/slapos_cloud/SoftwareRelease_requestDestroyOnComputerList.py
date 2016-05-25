portal = context.getPortalObject()
message = "Please select at least one computer."
dialog = dialog_id
item_count = 0
keep_items = {}
software_release = portal.portal_catalog.getResultValue(url_string=url_string,
                            portal_type='Software Release')

if len(uids) and software_release:  
  dialog = "SoftwareRelease_viewUsableComputerList"
  for computer in portal.portal_catalog(uid=uids, portal_type="Computer"):    
    # XXX - We won't destroy Software release if it used on this computer
    if not computer.Computer_getSoftwareReleaseUsage(software_release.getUrlString()):      
      computer.requestSoftwareRelease(software_release_url=url_string,
                                      state='destroyed')
      item_count += 1

  message = "Destruction request submited on %d computer(s)." % item_count

keep_items={'portal_status_message':context.Base_translateString(message)}
if cancel_url:
  keep_items['cancel_url'] = cancel_url

return context.Base_redirect(dialog, keep_items=keep_items)
