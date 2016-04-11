portal = context.getPortalObject()
person = portal.ERP5Site_getAuthenticatedMemberPersonValue()

if person is None:
  url = context.REQUEST.other["URL"]
  # Keep informations passed as query string and escape & with url code
  query_string = context.REQUEST.environ["QUERY_STRING"].replace("&","%26")
  # Redirect directly to browserid
  #context.REQUEST.RESPONSE.setCookie("redirect_after_login", context.REQUEST.form['callback_url'], path="/")
  return context.getWebSectionValue().Base_redirect("login_form?came_from=%s?%s" % (url,query_string))
else:
  info_dict = context.REQUEST.form
  software_type = info_dict.get("software_type")
  software_release = info_dict.get("software_release")
  parameter_hash = info_dict.get("parameter_hash")
  force_old = info_dict.get("force_old", None)

  if software_release.startswith("product."):
    software_release_list = context.SoftwareProduct_getSortedSoftwareReleaseList(software_product_reference=software_release[8:])
  elif force_old:
    software_release_list = [software_release]
  else:
    software_release_list = context.SoftwareProduct_getSortedSoftwareReleaseList(software_release_url=software_release)

  if len(software_release_list):
    software_release_document = software_release_list[0]

    message = context.Base_translateString("Define your initial Paramaters, and get your instances.")
    keep_item_dict = {"portal_status_message":  message,
        "software_type": software_type }

    if parameter_hash:
      keep_item_dict["parameter_hash"] = parameter_hash
  
    return software_release_document.Base_redirect(
      "SoftwareRelease_viewRequestDialog", keep_items=keep_item_dict)

raise ValueError("Unable to find the Software Release")
