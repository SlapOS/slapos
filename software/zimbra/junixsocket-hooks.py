# -*- coding: utf-8 -*-

import shutil
import os

import lxml


def fix_build_xml(options, sections):
    compile_directory = options['compile-directory']
    build_xml = os.path.join(compile_directory, 'junixsocket-1.3', 'build.xml')
    root = lxml.etree.parse(build_xml)
    junit = root.xpath('//property[@name="junit4.jar"]')[0]
    junit.set('value', options['junit-path'])

    with open(build_xml, 'wb') as fout:
        fout.write(lxml.etree.tostring(root))


def install_library(options, sections):
    compile_directory = options['compile-directory']
    filename = 'junixsocket-1.3-bin.tar.bz2'
    built_package = os.path.join(compile_directory, 'junixsocket-1.3', 'dist', filename)
    dst = os.path.join(options['location'], filename)
    shutil.copyfile(built_package, dst)
