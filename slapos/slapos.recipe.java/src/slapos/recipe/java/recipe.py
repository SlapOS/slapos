import logging
import os
import shutil
import zc.buildout.easy_install
import zc.buildout.download
from platform import uname
import subprocess

JAVA_URLS = {
        'x86': "http://javadl.sun.com/webapps/download/AutoDL?BundleId=48334",
        'x86-64': "http://javadl.sun.com/webapps/download/AutoDL?BundleId=48338"
}
# See http://java.com/en/download/manual.jsp

ARCH_MAP = {
    'i386': 'x86',
    'i586': 'x86',
    'i686': 'x86',
    'x86_64': 'x86-64'
}

ARCH_DIR_MAP = {
    'x86':'x86',
    'x86-64': 'x86_64'
}

class Recipe(object):
    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = options
        self.logger = logging.getLogger(self.name)

        options['location'] = os.path.join(
            buildout['buildout']['parts-directory'],
            self.name)
        options.setdefault('cpio', 'cpio')
        options.setdefault('tmp-storage', options['location'] + '__unpack__')
        if not options.get('download-url'):
            options.setdefault('platform', self._guessPackagePlatform())
            options.setdefault(
                'flavour',
                'oracle-jdk') # or 'openjdk'
            if options['flavour'] == 'openjdk':
                raise Exception('OpenJDK is not yet supported.')
            else:
                options['download-url'] = JAVA_URLS[options['platform']]
    
    def _guessPackagePlatform(self):
        arch = uname()[-2]
        target = ARCH_MAP.get(arch)
        assert target, 'Unknown architecture'
        return target
    
    def install(self):
        location = self.options['location']
        if os.path.exists(location):
            return location
        storage = self.options['tmp-storage']
        
        download_file, is_temp = self.download()
        
        self.extract(storage, download_file)
        self.copy(storage)
        shutil.rmtree(storage)
        return [location,]
    
    def download(self):
        """Download tarball. Caching if required.
        """
        url = self.options['download-url']
        namespace = self.options['recipe']
        download = zc.buildout.download.Download(self.buildout['buildout'],
                                                 namespace=namespace,
                                                 logger=self.logger)
        return download(url)
    
    def extract(self, storage, download_file):
        # Creates parts/java__something temp dir
        if os.path.exists(storage):
            shutil.rmtree(storage)
        os.mkdir(storage)
        os.chdir(storage)
        # Move downloaded file into temp dir
        (download_dir, filename) = os.path.split(download_file)
        auto_extract_bin = os.path.join(storage, filename)
        shutil.move(download_file, auto_extract_bin)
        # Run auto-extract bin file
        os.chmod(auto_extract_bin, 0777)
        subprocess.call([auto_extract_bin])
    
    def copy(self, storage):
        """Copy java installation into parts directory.
        """
        location = self.options['location']
        if os.path.exists(location):
            self.logger.info('No need to re-install java part')
            return False
        self.logger.info("Copying unpacked contents")
        java_dir = ''
        for java_dir in ('java', 'jre1.6.0_25'):
            if os.path.isdir(os.path.join(storage, java_dir)):
                break
        assert java_dir, 'Java directory seems missing.'
        ignore_dir_list = []
        if 'ignore' in shutil.copytree.func_code.co_varnames:
            shutil.copytree(os.path.join(storage, java_dir),
                            location,
                            ignore=lambda src,names:ignore_dir_list)
        else:
            shutil.copytree(os.path.join(storage, java_dir),
                            location)
            for ignore_dir in ignore_dir_list:
                ignore_dir = os.path.join(location, ignore_dir)
                if os.path.exists(ignore_dir):
                    shutil.rmtree(ignore_dir)
        return True
    
    def update(self):
        pass
