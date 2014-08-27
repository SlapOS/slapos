gitrepo
=======

This software release allow you to get a private mono-user git
repository with web interface.

This software release only need one parameter “repos”, which is
a json object of the repos and their description.

It can receive a “title” parameter as well in order to specify
a title for gitweb interface interface.

Example
--------

::
  repo = request(
      software_release=gitrepo,
      partiion_reference="My SlapGit",
      partition_parameter_kw={
        'repos': """
          {
            "repo": "description",
            "foo": "bar"
          }
        """,
        'title': 'optional title',
      }
  )

