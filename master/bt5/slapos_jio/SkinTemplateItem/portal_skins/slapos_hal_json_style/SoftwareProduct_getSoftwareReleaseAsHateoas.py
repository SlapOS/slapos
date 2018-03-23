import json

if software_release.startswith("product."):
  software_release_list = context.SoftwareProduct_getSortedSoftwareReleaseList(software_product_reference=software_release[8:])
else:
  software_release_list = context.SoftwareProduct_getSortedSoftwareReleaseList(software_release_url=software_release, strict=strict)

if len(software_release_list):
  software_release_document = software_release_list[0]

return json.dumps(software_release_document.getRelativeUrl())
