# -*- coding: utf-8 -*-

import sys
import os
import tempfile
import shutil

import test.test_support
inotifyw = test.test_support.import_module('inotifyw')
threading = test.test_support.import_module('threading')
import unittest

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self._threads = test.test_support.threading_setup()
        self.work_path = tempfile.mkdtemp()        
        self.work_path2 = tempfile.mkdtemp()        
        
    def tearDown(self):        
        test.test_support.threading_cleanup(*self._threads)
        test.test_support.reap_children()
        shutil.rmtree(self.work_path)
        shutil.rmtree(self.work_path2)        

class InotifywTests(BaseTestCase):

    def test_add_watch(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        self.assertEquals(wd, 0)        

    def test_rm_watch(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        self.assertEquals(inotifyw.rm_watch(fd, wd), 0)        

    def test_rm_watch_not_exists(self):
        fd = inotifyw.init()
        self.assertRaises(RuntimeError, inotifyw.rm_watch, fd, 0)        

    def test_rm_add_more_watches(self):
        fd = inotifyw.init()
        wd1 = inotifyw.add_watch(fd, self.work_path)
        wd2 = inotifyw.add_watch(fd, self.work_path2)
        self.assertEquals((wd1, wd2), (0, 1))

        self.assertEquals(inotifyw.rm_watch(fd, wd2), 1)
        self.assertEquals(inotifyw.rm_watch(fd, wd1), 0)        
        
    def test_rm_add_more_watches_2(self):
        fd = inotifyw.init()
        wd1 = inotifyw.add_watch(fd, self.work_path)
        wd2 = inotifyw.add_watch(fd, self.work_path2)
        self.assertEquals((wd1, wd2), (0, 1))

        self.assertEquals(inotifyw.rm_watch(fd, wd1), 0)
        self.assertEquals(inotifyw.rm_watch(fd, wd2), 0)        
        
    def test_get_events_nowait(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        self.assertEquals(inotifyw.get_events(fd, 0), [])        

    def test_get_events_timeout(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        self.assertEquals(inotifyw.get_events(fd, 1.0), [])        

    def test_notify_any_change(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        name = 'a'
        path = os.path.join(self.work_path, name)

        t = threading.Timer(1.0, lambda : os.mkdir(path))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_CREATE, 0, name))

        t = threading.Timer(1.0, lambda : os.rmdir(path))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_DELETE, 0, name))

        t = threading.Timer(1.0, lambda : tempfile.mkstemp(dir=self.work_path))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1], inotifyw.IN_CREATE)

        filename = e[0][3]
        wd = e[0][0]
        t = threading.Timer(1.0, lambda : os.remove(os.path.join(self.work_path, filename)))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0], (wd, inotifyw.IN_DELETE, 0, filename))        

    def test_notify_create_path(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_CREATE)
        name = 'a'
        path = os.path.join(self.work_path, name)

        t = threading.Timer(1.0, lambda : os.mkdir(path))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_CREATE, 0, name))        

    def test_notify_change_attribute(self):
        fd = inotifyw.init()
        fullpath = tempfile.mkstemp(dir=self.work_path)[1]
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_ATTRIB)

        t = threading.Timer(1.0, lambda : os.chmod(fullpath, 0777))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_ATTRIB, 0, os.path.split(fullpath)[1]))        

    def test_notify_in_modify(self):
        fd = inotifyw.init()
        fullpath = tempfile.mkstemp(dir=self.work_path)[1]
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_MODIFY)

        t = threading.Timer(1.0, lambda : os.utime(fullpath, None))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_MODIFY, 0, os.path.split(fullpath)[1]))        
        
    def test_notify_in_access(self):
        fd = inotifyw.init()
        fullpath = tempfile.mkstemp(dir=self.work_path)[1]
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_ACCESS)

        t = threading.Timer(1.0, lambda : os.utime(fullpath, None))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_ACCESS, 0, os.path.split(fullpath)[1]))        
        
    def test_notify_delete_file(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_DELETE)
        name = 'a'
        path = os.path.join(self.work_path, name)
        os.mkdir(path)

        t = threading.Timer(1.0, lambda : os.rmdir(path))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_DELETE, 0, name))

        fullpath = tempfile.mkstemp(dir=self.work_path)[1]
        t = threading.Timer(1.0, lambda : os.remove(fullpath))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0], (wd, inotifyw.IN_DELETE, 0, os.path.split(fullpath)[1]))        

    def test_notify_many_changes(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path)
        names = ('a', 'b', 'c')
        fullnames = [ os.path.join(self.work_path, s) for s in names ]
        ts = []
        for s in fullnames:
            ts.append(threading.Timer(1.0, lambda path=s: os.mkdir(path)))
        [ t.start() for t in ts ]
        e = inotifyw.get_events(fd, 5.0)
        self.assertEquals(len(e), 1)
        
    def test_notify_until_delete_file(self):
        fd = inotifyw.init()
        wd = inotifyw.add_watch(fd, self.work_path, inotifyw.IN_DELETE)
        name = 'a'
        t1 = threading.Timer(1.0, lambda : os.mkdir(os.path.join(self.work_path, name)))
        t2 = threading.Timer(3.0, lambda : os.rmdir(os.path.join(self.work_path, name)))
        [ t.start() for t in (t1, t2) ]
        e = inotifyw.get_events(fd)
        self.assertEquals(e[0][1:], (inotifyw.IN_DELETE, 0, name))        

    def test_notify_many_watches(self):
        fd = inotifyw.init()
        patha = self.work_path2
        pathb = self.work_path
        wd1 = inotifyw.add_watch(fd, patha, inotifyw.IN_CREATE)
        wd2 = inotifyw.add_watch(fd, pathb, inotifyw.IN_CREATE)
        name = 'test'
        fullpath = os.path.join(pathb, name)
        t = threading.Timer(1.5, lambda : os.mkdir(fullpath))
        t.start()
        e = inotifyw.get_events(fd, 3.0)
        self.assertEquals(e[0][1:], (inotifyw.IN_CREATE, 0, name))        

if __name__ == "__main__":
    # unittest.main()
    loader = unittest.TestLoader()
    # loader.testMethodPrefix = 'test_notify_many_watches'
    suite = loader.loadTestsFromTestCase(InotifywTests)
    unittest.TextTestRunner(verbosity=2).run(suite)

