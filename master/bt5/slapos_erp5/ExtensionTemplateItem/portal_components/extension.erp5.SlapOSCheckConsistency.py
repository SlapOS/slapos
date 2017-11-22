from App.config import getConfiguration


def getConfigurationCloudoooUrl(self):
  try:
    kw = getConfiguration().product_config['initsite']
  except KeyError:
    return

  return kw.get("cloudooo_url", None)