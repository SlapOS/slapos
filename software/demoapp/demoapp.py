#! /bin/python

import cgi
import os
import posixpath
import sys
import shutil
import subprocess
import tempfile
import urllib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

def get_disk_quota_report():
    show_disk_quota_script = """
    Set objWMIService = GetObject("winmgmts:\\\\.\\root\\cimv2")
    Set colDiskQuotas = objWMIService.ExecQuery("Select * from Win32_DiskQuota")

    For Each objQuota in colDiskQuotas
        Wscript.Echo "<p>User: " & objQuota.User & "</p>"
        Wscript.Echo "<p>Disk Space Used: " & objQuota.DiskSpaceUsed & "</p>"
        Wscript.Echo "<p>Limit: " & objQuota.Limit & "</p>"
        Wscript.Echo "<p>Quota Volume: " & objQuota.QuotaVolume & "</p>"
        Wscript.Echo "<p>Status: " & objQuota.Status & "</p>"
        Wscript.Echo "<p>Warning Limit: " & objQuota.WarningLimit & "</p>"
        Wscript.Echo "<p></p>"
    Next
    """

    f, filename = tempfile.mkstemp(suffix='.vbs')
    os.write(f, show_disk_quota_script)
    os.close(f)
    cmdlist = ('cyg_wscript', filename, '//Nologo')
    output = subprocess.check_output(cmdlist)
    os.unlink(filename)
    return output

class DemoHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.show_disk_quota(path)
        ctype = 'text/plain'
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def show_disk_quota(self, path):
        f = StringIO()
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>SlapOS Demo For Windows</title>\n")
        f.write("<body>\n<h2>Disk Quota List</h2>\n")
        f.write("<hr>\n")
        output = get_disk_quota_report()
        f.write(output)
        f.write("<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

class HTTPServerV6(HTTPServer):
  address_family = 23 # socket.AF_INET6

def run(server_class=HTTPServerV6,
        handler_class=DemoHTTPRequestHandler,
        addr='::',
        port=18000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()
    sys.exit(0)

