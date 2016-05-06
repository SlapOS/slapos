portal = context.getPortalObject()

error_list = []
portal_certificate_authority = getattr(portal, 'portal_certificate_authority', None)
promise_ca_path = portal.getPromiseParameter('portal_certificate_authority', 'certificate_authority_path')

def installCertificateAuthority():
  portal_certificate_authority = getattr(portal, 'portal_certificate_authority', None)
  if portal_certificate_authority is None:
    portal.manage_addProduct['ERP5'].manage_addTool('ERP5 Certificate Authority Tool', None)
    portal_certificate_authority = getattr(portal, 'portal_certificate_authority')
  
  portal_certificate_authority.manage_editCertificateAuthorityTool(
     certificate_authority_path=promise_ca_path)


if promise_ca_path is not None:
  if portal_certificate_authority is None:
    error_list.append("Certificate Authority Tool is not present")

  elif portal_certificate_authority.certificate_authority_path != promise_ca_path:
    error_list.append(
      "Certificate Authority Tool (OpenSSL)is not configured as Expected: %s" %
        "Expect %s\nGot %s" % (portal_certificate_authority.certificate_authority_path, promise_ca_path))

if len(error_list) > 0 and fixit:
  installCertificateAuthority()
return error_list
