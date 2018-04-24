query_kw = dict()

if software_instance_portal_type == "Slave Instance" and\
   software_release_url == "http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg":

  software_release_list = context.SoftwareProduct_getSortedSoftwareReleaseList(software_product_reference="frontend")

  if len(software_release_list):
    software_release_document = software_release_list[0]

  query_kw['software_release_url'] = software_release_document.getUrlString()

  # This should be adjusted
  query_kw['software_type'] = "custom-personal"
  return query_kw

return query_kw
