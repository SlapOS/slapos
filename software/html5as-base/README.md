# Html5 Application Server #

## Presentation ##

* Fast hosting software for static website (html5)

* Use Nginx server

## Parameter ##

download_url (string) :required

Details :

* Only tarball (tar) is supported

* Compressed format is gunzip (optional)

* Tarball must contain an index.html at its root

## How it works ##

Each time you (re)start your instance or update parameters, html5as will remove previous website then download tarball and extract it in docroot directory.
