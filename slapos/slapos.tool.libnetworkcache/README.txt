Introduction
==============
The goal of libnetworkcache python library is to abstract the REST calls.
It works as wrapper of python httplib to use the Networkcache HTTP Server.

API
======
So, it must provide 2 methods:

 put(file)
 ''' Upload the file to Networkcache HTTP Server using PUT as HTTP method.'''

 get(key)
 ''' Download the file from Networkcache HTTP Server using GET as HTTP method.''' 
