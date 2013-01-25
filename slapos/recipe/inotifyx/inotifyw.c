/*
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include <Python.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/cygwin.h>

/* Avoid select function conflict in the winsock2.h */
#define __INSIDE_CYGWIN__
#include <windows.h>

/* the following are legal, implemented events that user-space can watch for */
#define IN_ACCESS		0x00000001	/* File was accessed */
#define IN_MODIFY		0x00000002	/* File was modified */
#define IN_ATTRIB		0x00000004	/* Metadata changed */
#define IN_CLOSE_WRITE		0x00000008	/* Writtable file was closed */
#define IN_CLOSE_NOWRITE	0x00000010	/* Unwrittable file closed */
#define IN_OPEN			0x00000020	/* File was opened */
#define IN_MOVED_FROM		0x00000040	/* File was moved from X */
#define IN_MOVED_TO		0x00000080	/* File was moved to Y */
#define IN_CREATE		0x00000100	/* Subfile was created */
#define IN_DELETE		0x00000200	/* Subfile was deleted */
#define IN_DELETE_SELF		0x00000400	/* Self was deleted */
#define IN_MOVE_SELF            0x00000800

/* the following are legal events.  they are sent as needed to any watch */
#define IN_UNMOUNT		0x00002000	/* Backing fs was unmounted */
#define IN_Q_OVERFLOW		0x00004000	/* Event queued overflowed */
#define IN_IGNORED		0x00008000	/* File was ignored */

/* helper events */
#define IN_CLOSE		(IN_CLOSE_WRITE | IN_CLOSE_NOWRITE) /* close */
#define IN_MOVE			(IN_MOVED_FROM | IN_MOVED_TO) /* moves */

/* special flags */
#define IN_ONLYDIR               0x01000000
#define IN_DONT_FOLLOW           0x02000000
#define IN_EXCL_UNLINK           0x04000000
#define IN_ISDIR		 0x40000000	/* event occurred against dir */
#define IN_MASK_ADD              0x20000000
#define IN_ONESHOT		 0x80000000	/* only send event once */

/*
 * All of the events - we build the list by hand so that we can add flags in
 * the future and not break backward compatibility.  Apps will get only the
 * events that they originally wanted.  Be sure to add new events here!
 */
#define IN_ALL_EVENTS   (IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE | IN_CREATE \
                         | IN_ACCESS | IN_MODIFY)

#define ALIGN_CLUSPROP( count ) (((count) + 3) & ~3)

#define WATCH_BUFFER_SIZE        0x4000 /* 16K */

typedef struct _WATCH_DESCRIPTOR {
  int watch_id;                 /* Internal ID */
  uint32_t mask;
  size_t len;                   /* Length of path in bytes */
  wchar_t  path[2];             /* Variable length */
} WATCH_DESCRIPTOR, *PWATCH_DESCRIPTOR;

typedef struct _INOTIFY_OBJECT {
  size_t size;                  /* Total size of object */
  int last_id;                  /* Last watch id */
  int count;                    /* Watch counter */
} INOTIFY_OBJECT, *PINOTIFY_OBJECT;

const char * WAIT_EVENT_NAMES[2] = {
  "monitor_thread_event_notify_path_changed_or_thread_started",
  "main_thread_event_notify_monitor_thread_quit"
};

#define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
#define FREE(x) HeapFree(GetProcessHeap(), 0, (x))

static void
print_windows_error()
{
    // Retrieve the system error message for the last-error code
    LPVOID lpMsgBuf;
    DWORD dw = GetLastError();

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR) &lpMsgBuf,
        0,
        NULL
        );
    printf("Windows Error:%s\n", (const char*)lpMsgBuf);
    LocalFree(lpMsgBuf);
}

static PyObject *
set_windows_exception()
{
    // Retrieve the system error message for the last-error code
    LPVOID lpMsgBuf;
    DWORD dw = GetLastError();

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR) &lpMsgBuf,
        0,
        NULL
        );
    PyErr_SetString(PyExc_RuntimeError, (const char*)lpMsgBuf);
    LocalFree(lpMsgBuf);
    return NULL;
}

static DWORD
map_mask_to_filter(uint32_t mask)
{
  if (mask & (IN_OPEN | IN_CLOSE_WRITE | IN_CLOSE_NOWRITE | IN_DELETE_SELF))
    return -1;

  DWORD filter = 0;
  if (mask & IN_ACCESS)
    filter |= FILE_NOTIFY_CHANGE_LAST_ACCESS;
  if (mask & IN_MODIFY)
    filter |= FILE_NOTIFY_CHANGE_LAST_WRITE;
  if (mask & IN_ATTRIB)
    filter |= FILE_NOTIFY_CHANGE_ATTRIBUTES;
  if (mask & (IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE | IN_CREATE))
    filter |= FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_DIR_NAME;

  return filter;
}

static uint32_t
map_action_to_mask(uint32_t mask, DWORD action)
{
  uint32_t result = 0;

  switch(action){
  case FILE_ACTION_ADDED:
    return IN_CREATE;
  case FILE_ACTION_REMOVED:
    return IN_DELETE;
  case FILE_ACTION_MODIFIED:
    if (mask & IN_ATTRIB)
      result |= IN_ATTRIB;
    if (mask & IN_ACCESS)
      result |= IN_ACCESS;
    if (mask & IN_MODIFY)
      result |= IN_MODIFY;
    return result;
  case FILE_ACTION_RENAMED_OLD_NAME:
    return IN_MOVED_FROM;
  case FILE_ACTION_RENAMED_NEW_NAME:
    return IN_MOVED_TO;
  default:
    return 0;
  }
}

static void
free_cobject(void * p)
{
  assert(p);
  FREE(p);
}

static PyObject *
inotifyw_init(PyObject *self, PyObject *args)
{
  PINOTIFY_OBJECT pnotify = (PINOTIFY_OBJECT)MALLOC(WATCH_BUFFER_SIZE);
  if (pnotify == NULL)
    return PyErr_NoMemory();

  ZeroMemory((void*)pnotify, WATCH_BUFFER_SIZE);
  pnotify -> size = sizeof(INOTIFY_OBJECT);

  return PyCObject_FromVoidPtr(pnotify, free_cobject);
}

static PyObject *
inotifyw_add_watch(PyObject *self, PyObject *args)
{
  PyObject *pobj = NULL;
  char *path;
  ssize_t size;
  uint32_t mask;

  PINOTIFY_OBJECT pnotify;
  PWATCH_DESCRIPTOR pwatch;

  mask = IN_ALL_EVENTS;

  if(! PyArg_ParseTuple(args, "Os|i", &pobj, &path, &mask))
    return NULL;

  if (! PyCObject_Check(pobj))
    return NULL;

  /* Check mask by mapping mask to NotifyFilter */
  DWORD filter = map_mask_to_filter(mask);
  if ((filter == -1) || (filter == 0)) {
    PyErr_SetString(PyExc_RuntimeError, "unsupport flags");
    return NULL;
  }

  /* Map posix path to win path.

     In the Windows API, the maximum length for a path is MAX_PATH,
     which is defined as 260 characters.

     The Windows API has many functions that also have Unicode
     versions to permit an extended-length path for a maximum total
     path length of 32,767 characters. This type of path is composed
     of components separated by backslashes, each up to the value
     returned in the lpMaximumComponentLength parameter of the
     GetVolumeInformation function (this value is commonly 255
     characters). To specify an extended-length path, use the "\\?\"
     prefix. For example, "\\?\D:\very long path".

     http://msdn.microsoft.com/en-us/library/aa365247(v=vs.85).aspx
     */
  size = cygwin_conv_path (CCP_POSIX_TO_WIN_W, path, NULL, 0);
  if (size < 0){
    PyErr_SetString(PyExc_RuntimeError, "cygwin_conv_path failed");
    return NULL;
  }

  /* Let size to be DWORD-Aligned  */
  size = ALIGN_CLUSPROP(size);

  pnotify = (PINOTIFY_OBJECT)PyCObject_AsVoidPtr(pobj);
  if (pnotify -> size + sizeof(WATCH_DESCRIPTOR) + size > WATCH_BUFFER_SIZE) {
    PyErr_SetString(PyExc_RuntimeError, "no sapce to add watch");
    return NULL;
  }

  pwatch = (PWATCH_DESCRIPTOR)((void*)pnotify + pnotify -> size);
  if (cygwin_conv_path (CCP_POSIX_TO_WIN_W, path, pwatch -> path, size)){
    PyErr_SetString(PyExc_RuntimeError, "cygwin_conv_path");
    return NULL;
  }

  pwatch -> watch_id = pnotify -> last_id;
  pwatch -> mask = mask;
  pwatch -> len = size;

  pnotify -> size += sizeof(WATCH_DESCRIPTOR) + size;
  pnotify -> last_id ++;
  pnotify -> count ++;

  return Py_BuildValue("i", pwatch -> watch_id);
}


static PyObject *
inotifyw_rm_watch(PyObject *self, PyObject *args)
{
  PyObject *pobj = NULL;
  uint32_t watch_id;
  int index;
  size_t size;
  size_t offset;

  PWATCH_DESCRIPTOR pwatch;
  PINOTIFY_OBJECT pnotify;

  if(! PyArg_ParseTuple(args, "Oi", &pobj, &watch_id))
    return NULL;

  if (! PyCObject_Check(pobj))
    return NULL;

  pnotify = (PINOTIFY_OBJECT)PyCObject_AsVoidPtr(pobj);
  pwatch = (PWATCH_DESCRIPTOR)((void*)pnotify + sizeof(INOTIFY_OBJECT));

  index = pnotify -> count;
  while (index) {

    size =  + sizeof(WATCH_DESCRIPTOR) + pwatch -> len;

    if (pwatch -> watch_id == watch_id){

      pnotify -> count --;
      pnotify -> size -= size;

      memcpy((void*)pwatch,
             (void*)pwatch + size,
             pnotify -> size - ((void*)pwatch - (void*)pnotify)
             );

      return Py_BuildValue("i", pnotify -> count - index + 1);
    }

    index --;
    pwatch = (PWATCH_DESCRIPTOR)((void*)pwatch + size);
  }

  PyErr_SetString(PyExc_RuntimeError, "no such watch descriptor");
  return NULL;
}

static int
format_inotify_event(PyObject *pret,
                     PWATCH_DESCRIPTOR pwatch,
                     PFILE_NOTIFY_INFORMATION pinfo)
{
  PyObject *value = NULL;
  ssize_t size;
  char *target_path;
  wchar_t *wfilename;
  uint32_t mask;
  int counter = 0;

  while (1) {

    mask = map_action_to_mask(pwatch -> mask, pinfo -> Action);

    if (pwatch -> mask & mask){

      counter ++;

      if (pinfo -> FileNameLength) {

        /* Null-Terminated File Name */
        wfilename = (wchar_t*)MALLOC(pinfo -> FileNameLength + 2);
        if (wfilename == NULL) {
          PyErr_NoMemory();
          return -1;
        }
        memcpy(wfilename, pinfo -> FileName, pinfo -> FileNameLength);
        *(wfilename + pinfo -> FileNameLength / 2) = 0;

        /* Conversion from incoming Win32 path given as wchar_t *win32 to
           POSIX path.  First ask how big the output buffer has to be and
           allocate space dynamically. */
        size = cygwin_conv_path (CCP_WIN_W_TO_POSIX, wfilename, NULL, 0);
        if (size < 0) {
          FREE(wfilename);
          PyErr_SetString(PyExc_RuntimeError, "cygwin_conv_path failed");
          return -1;
        }
        target_path = (char *)MALLOC(size);
        if (target_path == NULL) {
          FREE(wfilename);
          PyErr_NoMemory();
          return -1;
        }
        ZeroMemory((void*)target_path, size);
        if (cygwin_conv_path (CCP_WIN_W_TO_POSIX | CCP_RELATIVE,
                              wfilename,
                              target_path,
                              size)) {
          PyErr_SetString(PyExc_RuntimeError, "cygwin_conv_path failed");
          return -1;
        }

        value = Py_BuildValue("iiis",
                              pwatch -> watch_id,
                              mask,
                              0,
                              target_path
                              );
        FREE(target_path);
      }

      else
        value = Py_BuildValue("iiiO",
                              pwatch -> watch_id,
                              mask,
                              0,
                              Py_None
                              );
      FREE(wfilename);
      if ((value == NULL) || (PyList_Append(pret, value) < 0))
        return -1;
    }

    if (pinfo -> NextEntryOffset == 0)
      break;

    pinfo = (PFILE_NOTIFY_INFORMATION)((void*)pinfo+pinfo->NextEntryOffset);
  }

  return counter;
}


DWORD WINAPI
ThreadProc(LPVOID lpParam)
{
  DWORD filter = 0;
  BOOL subtree = TRUE;
  int i;

  uint32_t count;

  void *pbuffer = NULL;
  size_t bufsize;

  HANDLE *phandles;
  HANDLE *events;
  HANDLE *pevents;
  PWATCH_DESCRIPTOR *pwatches;
  OVERLAPPED *poverlappeds;

  void *output;
  PFILE_NOTIFY_INFORMATION pinfo;
  size_t outbufsize = 0;

  HRESULT hr = S_OK;
  PINOTIFY_OBJECT pnotify = (PINOTIFY_OBJECT)lpParam;

  DWORD dwExitCode = 0;

  /* Allocate space for handles, events and overlappeds */
  count = pnotify -> count;
  bufsize = (sizeof(OVERLAPPED) + sizeof(PWATCH_DESCRIPTOR) +
             sizeof(HANDLE)) * count + sizeof(HANDLE) * 2;
  pbuffer = MALLOC(bufsize);
  if (pbuffer == NULL)
    return 1;
  ZeroMemory(pbuffer, bufsize);

  phandles = (HANDLE*)pbuffer;
  events = phandles + count;
  pevents = events + 2;
  pwatches = (PWATCH_DESCRIPTOR*)((void*)pevents + sizeof(HANDLE) * count);
  poverlappeds = (OVERLAPPED*)((void*)pwatches + sizeof(PWATCH_DESCRIPTOR) * count);

  /* Allocate space for output, after detect path changed, the
     information will be copied to rest space of pnotify object. */
  output = (void*)pnotify + ALIGN_CLUSPROP(pnotify -> size);
  outbufsize = WATCH_BUFFER_SIZE - ALIGN_CLUSPROP(pnotify -> size);
  pinfo = (PFILE_NOTIFY_INFORMATION)MALLOC(outbufsize);
  if (pinfo == NULL) {
    FREE(pbuffer);
    return 2;
  }
  ZeroMemory(pinfo, outbufsize);

  events[0] = CreateEvent(NULL, TRUE, FALSE, WAIT_EVENT_NAMES[0]);
  events[1] = CreateEvent(NULL, TRUE, FALSE, WAIT_EVENT_NAMES[1]);

  if ((events[0] == NULL) || (events[1] == NULL)) {
    FREE(pbuffer);
    FREE(pinfo);
    return 3;
  }

  /* Notify main thread it's ready */
  if (!SetEvent(events[0])) {
    CloseHandle(events[0]);
    CloseHandle(events[1]);
    FREE(pbuffer);
    FREE(pinfo);
    return 4;
  }

  // Init watch events
  PWATCH_DESCRIPTOR p;
  p = (PWATCH_DESCRIPTOR)((void*)pnotify + sizeof(INOTIFY_OBJECT));

  /* pinfo is used as parameter "lpBuffer" of ReadDirectoryChangesW

     lpBuffer [out]

     A pointer to the DWORD-aligned formatted buffer in which the read
     results are to be returned. The structure of this buffer is
     defined by the FILE_NOTIFY_INFORMATION structure.

     Read above document carefully, lpBuffer must BE DWORD-aligned. I
     have made this mistake, and be curious why ReadDirectoryChangesW
     doesn't work. I had spent almost one day to resolve it before I
     knew it. You'll not aware of it when using malloc, but allocate
     space by yourself, it's coming.
  */
  for (i = 0; i < count; i++){

    // Open directory handle
    phandles[i] = CreateFileW(p -> path,
                              FILE_LIST_DIRECTORY | GENERIC_READ,
                              FILE_SHARE_READ |
                              FILE_SHARE_WRITE |
                              FILE_SHARE_DELETE,
                              NULL,
                              OPEN_EXISTING,
                              FILE_FLAG_BACKUP_SEMANTICS |
                              FILE_FLAG_OVERLAPPED,
                              NULL
                              );

    if (phandles[i] == INVALID_HANDLE_VALUE){
      hr = S_FALSE;
      dwExitCode = 5;
      break;
    }

    pevents[i] = CreateEvent(NULL, TRUE, FALSE, NULL);

    if (pevents[i] == NULL){
      hr = S_FALSE;
      dwExitCode = 6;
      break;
    }

    pwatches[i] = p;
    p = (PWATCH_DESCRIPTOR)((void*)p + sizeof(WATCH_DESCRIPTOR) + p -> len);
  }

  /* Loop for waiting changes of watched path */
  DWORD waitResult;
  DWORD dwBytesReturned;
  while (hr == S_OK) {

    ZeroMemory((void*)poverlappeds, sizeof(OVERLAPPED) * count);
    for (i = 0; i < count; i++) {

      poverlappeds[i].hEvent = pevents[i];
      //
      // Get information that describes the most recent file change
      // This call will return immediately and will set
      // overlapped.hEvent when it has completed
      //
      if (0 ==  ReadDirectoryChangesW(phandles[i],
                                      pinfo,
                                      outbufsize,
                                      subtree,
                                      map_mask_to_filter(pwatches[i] -> mask),
                                      &dwBytesReturned,
                                      (LPOVERLAPPED)(poverlappeds + i),
                                      NULL
                                      )){
        hr = S_FALSE;
        dwExitCode = 7;
        break;
      }
    }

    if (S_OK == hr) {
      waitResult = WaitForMultipleObjects(count + 1,
                                          events + 1,
                                          FALSE,
                                          INFINITE
                                          );

      if (waitResult == WAIT_OBJECT_0)
        break;

      else if ((waitResult > WAIT_OBJECT_0) &&
               (waitResult < WAIT_OBJECT_0 + count + 1)) {

        // Retrieve result from overlapped structure
        DWORD dwBytesTransferred = 0;
        uint32_t index = waitResult - 1;

        if (GetOverlappedResult(phandles[index],
                                poverlappeds + index,
                                &dwBytesTransferred,
                                TRUE
                                )) {

          /* Check whether main thread is idle */
          if (WaitForSingleObject(events[0], 0) == WAIT_TIMEOUT) {

            ((PWATCH_DESCRIPTOR*)output)[0] = pwatches[index];
            memcpy(output + sizeof(PWATCH_DESCRIPTOR),
                   pinfo,
                   dwBytesTransferred
                   );

            if (SetEvent(events[0])) {
              ResetEvent(pevents[index]);
              continue;
            }
          }
        }
      }

      // case 1: WaitForMultipleObjects failed
      // case 2: GetOverlappedResult failed
      // case 3: Main thread haven't reset events[0]
      // case 4: SetEvent events[0] failed
      dwExitCode = 8;
      hr = S_FALSE;
    }
  }

  // Cleanup
  assert(pbuffer);
  for (i = 0; i < count; i++) {
    if (pevents[i])
      CloseHandle(pevents[i]);
    if (phandles[i])
      CloseHandle(phandles[i]);
  }
  
  assert(pinfo);
  FREE(pinfo);
  FREE(pbuffer);

  SetEvent(events[0]);
  CloseHandle(events[0]);
  CloseHandle(events[1]);

  return dwExitCode;
}

static PyObject *
inotifyw_get_events(PyObject *self, PyObject *args)
{
  PyObject *pobj;
  float timeouts = INFINITE;
  PyObject *retvalue = NULL;
  int retcode;
  void *pwatch;
  void *pinfo;

  if(! PyArg_ParseTuple(args, "O|f", &pobj, &timeouts))
    return NULL;

  if (! PyCObject_Check(pobj))
    return NULL;

  PINOTIFY_OBJECT pnotify = (PINOTIFY_OBJECT)PyCObject_AsVoidPtr(pobj);
  if (pnotify -> count == 0)
    return PyList_New(0);

  HANDLE hevents[2];
  DWORD dwWaitResult;
  DWORD dwMilliseconds;
  DWORD dwThreadID;
  DWORD dwExitCode;
  HANDLE hThread = NULL;
  HRESULT hr = S_OK;

  Py_BEGIN_ALLOW_THREADS;
  hevents[0] = CreateEvent(NULL, TRUE, FALSE, WAIT_EVENT_NAMES[0]);
  hevents[1] = CreateEvent(NULL, TRUE, FALSE, WAIT_EVENT_NAMES[1]);
  Py_END_ALLOW_THREADS;

  if ((hevents[0] == NULL) || (hevents[0] == NULL)){
    set_windows_exception();
    hr = S_FALSE;
  }

  // Create monitor thread to watch path changes
  if (hr == S_OK) {
    hThread = CreateThread(NULL,              // default security
                           0,                 // stack size
                           ThreadProc,        // name of the thread function
                           (LPVOID)pnotify,
                           0,                 // startup flags
                           &dwThreadID);
    if (hThread == NULL){
      set_windows_exception();
      hr = S_FALSE;
    }
  }

  /* Wait monitor thread to work for 3 seconds */
  if (hr == S_OK) {

    Py_BEGIN_ALLOW_THREADS;
    dwWaitResult = WaitForSingleObject(hevents[0], 3000);
    Py_END_ALLOW_THREADS;

    if (! ((dwWaitResult == WAIT_OBJECT_0) && ResetEvent(hevents[0]))) {
      // case 1: WaitForSingleObject failed
      // case 2: monitor thread exception
      // case 3: monitor thread hasn't been executed, maybe os is busy
      // case 4: ResetEvent failed
      PyErr_SetString(PyExc_RuntimeError, "inotifyw starts exception");
      hr = S_FALSE;
    }
  }

  if (hr == S_OK) {

    dwMilliseconds = timeouts == INFINITE ? INFINITE : timeouts * 1000;
    pwatch = (void*)pnotify + ALIGN_CLUSPROP(pnotify -> size);
    pinfo = pwatch + sizeof(PWATCH_DESCRIPTOR);
  }

  // Loop for change notifications
  while (hr == S_OK) {

    Py_BEGIN_ALLOW_THREADS;
    dwWaitResult = WaitForSingleObject(hevents[0], dwMilliseconds);
    Py_END_ALLOW_THREADS;

    Py_BEGIN_ALLOW_THREADS;
    if (! (GetExitCodeThread(hThread, &dwExitCode)      \
           && (dwExitCode == STILL_ACTIVE)))
      hr = S_FALSE;
    Py_END_ALLOW_THREADS;

    if (S_FALSE == hr) {
      PyErr_SetString(PyExc_RuntimeError, "monitor thread exception");
      break;
    }

    if (dwWaitResult == WAIT_TIMEOUT) {
      retvalue = PyList_New(0);
      break;
    }

    else if (dwWaitResult == WAIT_OBJECT_0) {

      if ((retvalue = PyList_New(0)) == NULL) {
        hr = S_FALSE;
        break;
      }

      retcode =format_inotify_event(retvalue,
                                    ((PWATCH_DESCRIPTOR*)pwatch)[0],
                                    (PFILE_NOTIFY_INFORMATION)pinfo
                                    );

      if (retcode > 0)
        break;

      else if (retcode == 0) {

        if (dwMilliseconds == INFINITE){

          Py_XDECREF(retvalue);
          retvalue = NULL;

          if (ResetEvent(hevents[0]))
            continue;

          set_windows_exception();
          hr = S_FALSE;
        }
        break;
      }

      else
        hr = S_FALSE;
    }

    else {
      set_windows_exception();
      hr == S_FALSE;
    }
  }

  // Notify monitor thread to quit
  if (hThread){
    Py_BEGIN_ALLOW_THREADS;
    SetEvent(hevents[1]);
    CloseHandle(hThread);
    Py_END_ALLOW_THREADS;
  }

  // Clean up
  Py_BEGIN_ALLOW_THREADS;
  CloseHandle(hevents[0]);
  CloseHandle(hevents[1]);
  Py_END_ALLOW_THREADS;

  return retvalue;
}

static PyMethodDef InotifyMethods[] = {
  {
    "init",
    inotifyw_init,
    METH_VARARGS,
    (
     "init()\n\n"
     "Initialize an inotify instance and return a PyCObject, When this\n"
     "PyCObject is reclaimed, GC will free the memory.\n"
     )
  },
  {
    "add_watch",
    inotifyw_add_watch,
    METH_VARARGS,
    (
     "add_watch(fd, path[, mask])\n\n"
     "Add a watch for path and return the watch descriptor.\n"
     "fd should be the object returned by init.\n"
     "If left unspecified, mask defaults to IN_ALL_EVENTS.\n"
     "See the inotifyw documentation for details."
     )
  },
  {
    "rm_watch",
    inotifyw_rm_watch,
    METH_VARARGS,
    (
     "rm_watch(fd, wd)\n\n"
     "Remove the watch associated with watch descriptor wd.\n"
     "fd should be the object returned by init.\n"
     )
  },
  {
    "get_events",
    inotifyw_get_events,
    METH_VARARGS,
    "get_events(fd[, timeout])\n\n"
    "Read events from inotify and return a list of tuples "
    "(wd, mask, cookie, name).\n"
    "The name field is None if no name is associated with the inotify event.\n"
    "Timeout specifies a timeout in seconds (as an integer or float).\n"
    "If left unspecified, there is no timeout and get_events will block\n"
    "indefinitely.  If timeout is zero, get_events will not block."
  },
  {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initinotifyw(void)
{
  PyObject* module;
  module = Py_InitModule3("inotifyw",
                          InotifyMethods,
                          "Low-level interface to inotify in the Windows."
                          );

  if (module == NULL)
    return;

  PyModule_AddIntConstant(module, "IN_ACCESS", IN_ACCESS);
  PyModule_AddIntConstant(module, "IN_MODIFY", IN_MODIFY);
  PyModule_AddIntConstant(module, "IN_ATTRIB", IN_ATTRIB);
  PyModule_AddIntConstant(module, "IN_CLOSE_WRITE", IN_CLOSE_WRITE);
  PyModule_AddIntConstant(module, "IN_CLOSE_NOWRITE", IN_CLOSE_NOWRITE);
  PyModule_AddIntConstant(module, "IN_CLOSE", IN_CLOSE);
  PyModule_AddIntConstant(module, "IN_OPEN", IN_OPEN);
  PyModule_AddIntConstant(module, "IN_MOVED_FROM", IN_MOVED_FROM);
  PyModule_AddIntConstant(module, "IN_MOVED_TO", IN_MOVED_TO);
  PyModule_AddIntConstant(module, "IN_MOVE", IN_MOVE);
  PyModule_AddIntConstant(module, "IN_CREATE", IN_CREATE);
  PyModule_AddIntConstant(module, "IN_DELETE", IN_DELETE);
  PyModule_AddIntConstant(module, "IN_DELETE_SELF", IN_DELETE_SELF);
  PyModule_AddIntConstant(module, "IN_MOVE_SELF", IN_MOVE_SELF);
  PyModule_AddIntConstant(module, "IN_UNMOUNT", IN_UNMOUNT);
  PyModule_AddIntConstant(module, "IN_Q_OVERFLOW", IN_Q_OVERFLOW);
  PyModule_AddIntConstant(module, "IN_IGNORED", IN_IGNORED);
  PyModule_AddIntConstant(module, "IN_ONLYDIR", IN_ONLYDIR);
  PyModule_AddIntConstant(module, "IN_DONT_FOLLOW", IN_DONT_FOLLOW);
  PyModule_AddIntConstant(module, "IN_MASK_ADD", IN_MASK_ADD);
  PyModule_AddIntConstant(module, "IN_ISDIR", IN_ISDIR);
  PyModule_AddIntConstant(module, "IN_ONESHOT", IN_ONESHOT);
  PyModule_AddIntConstant(module, "IN_ALL_EVENTS", IN_ALL_EVENTS);
}
