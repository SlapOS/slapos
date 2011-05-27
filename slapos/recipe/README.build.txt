build
=====

Recipe to build the software.

Example buildout::

  [buildout]
  parts =
    file

  [zlib]
  # Use standard configure, make, make install way
  recipe = slapos.cookbook:build
  url = http://prdownloads.sourceforge.net/libpng/zlib-1.2.5.tar.gz?download
  md5sum = c735eab2d659a96e5a594c9e8541ad63
  slapos_promisee =
    directory:include
    file:include/zconf.h
    file:include/zlib.h
    directory:lib
    statlib:lib/libz.a
    dynlib:lib/libz.so linked:libc.so.6 rpath:
    dynlib:lib/libz.so.1 linked:libc.so.6 rpath:
    dynlib:lib/libz.so.1.2.5 linked:libc.so.6
    directory:lib/pkgconfig
    file:lib/pkgconfig/zlib.pc
    directory:share
    directory:share/man
    directory:share/man/man3
    file:share/man/man3/zlib.3

  [file]
  recipe = slapos.cookbook:buildcmmi
  url = ftp://ftp.astron.com/pub/file/file-5.04.tar.gz
  md5sum = accade81ff1cc774904b47c72c8aeea0
  environment =
    CPPFLAGS=-I${zlib:location}/include
    LDFLAGS=-L${zlib:location}/lib -Wl,-rpath -Wl,${zlib:location}/lib
  slapos_promisee =
    directory:bin
    dynlib:bin/file linked:libz.so.1,libc.so.6,libmagic.so.1 rpath:${zlib:location}/lib,!/lib
    directory:include
    file:include/magic.h
    directory:lib
    statlib:lib/libmagic.a
    statlib:lib/libmagic.la
    dynlib:lib/libmagic.so linked:libz.so.1,libc.so.6 rpath:${zlib:location}/lib
    dynlib:lib/libmagic.so.1 linked:libz.so.1,libc.so.6 rpath:${zlib:location}/lib
    dynlib:lib/libmagic.so.1.0.0 linked:libz.so.1,libc.so.6 rpath:${zlib:location}/lib
    directory:share
    directory:share/man
    directory:share/man/man1
    file:share/man/man1/file.1
    directory:share/man/man3
    file:share/man/man3/libmagic.3
    directory:share/man/man4
    file:share/man/man4/magic.4
    directory:share/man/man5
    directory:share/misc
    file:share/misc/magic.mgc

  [somethingelse]
  # default way with using script
  recipe = slapos.cookbook:build
  url_0 = http://host/path/file.tar.gz
  md5sum = 9631070eac74f92a812d4785a84d1b4e
  script =
    import os
    os.chdir(%(work_directory)s)
    unpack(%(url_0), strip_path=True)
    execute('make')
    execute('make install DEST=%(location)s')
  slapos_promisee =
    ...

TODO:

 * add linking suport, buildout definition:

slapos_link = <relative/path> [optional-path

can be used as::

  [file]
  slapos_link =
    bin/file
    bin/file ${buildout:bin-directory}/bin/anotherfile

Which will link ${file:location}/bin/file to ${buildout:bin-directory}/bin/file
and ${file:location}/bin/file to ${buildout:bin-directory}/bin/anotherfile
