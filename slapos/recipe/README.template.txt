slapos.recipe.template
======================

Fully networked template recipe, reusing collective.recipe.template with
ability to download template over the network

Usage
-----

  [buildout]
  parts = template

  [template]
  recipe = slapos.recipe.template
  url = http://server/with/template
  # optional md5sum
  md5sum = 1234567890
  output = ${buildout:directory}/result

All parameters except url and md5sum will be passed to
collective.recipe.template, so please visit
http://pypi.python.org/pypi/collective.recipe.template for full information.
