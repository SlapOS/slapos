slapos.recipe.download
======================

Extremely simple recipe to download using zc.buildout download utility.

Usage
-----

  [buildout]
  parts =
    download

  [download]
  recipe = slapos.recipe.download
  url = https://some.url/file

Such profile will download https://some.url/file and put it in
buildout:parts-directory/download/download

filename parameter can be used to change destination named filename.

destination parameter allows to put explicit destination.

md5sum parameter allows pass md5sum.

mode (octal, so for rw-r--r-- use 0644) allows to set mode

Exposes target attribute which is path to downloaded file.

Notes
-----

This recipe suffers from buildout download utility issue, which will do not
try to redownload resource with wrong md5sum.
