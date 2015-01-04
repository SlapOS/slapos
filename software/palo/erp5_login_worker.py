#!${buildout:executable}
import sys
import xmlrpclib
import logging
import csv
import hashlib
import socket


def main():
  logfile = sys.argv[1]
  logging.basicConfig(filename=logfile,
                      format='%(asctime)s [%(levelname)s] %(message)s')
  logger = logging.getLogger('erp5_palo_login_worker')
  logger.setLevel(logging.DEBUG)

  erp5 = xmlrpclib.ServerProxy(sys.argv[2])

  ostream = sys.stdout
  def output(line):
    print >> ostream, line
    ostream.flush()

  istream = sys.stdin
  def stdin_reader():
    yield istream.readline()

  while True:
    try:
      csv_reader = csv.reader(stdin_reader(), delimiter=";")
      line = csv_reader.next()
      if not line:
        output('DONE')
        logger.info("Exiting")
        break
      cmd = line[0]
      args = line[1:]
      if cmd == 'SESSION':
        session_id = args[0]
        logger.debug("SESSION %r" % (session_id, ))
      elif cmd == 'AUTHORIZATION':
        login, password = args

        if login == 'admin':
          # XXX better way ?
  #        admin_pass = "admin"
  #        authentication_success = hashlib.md5(admin_pass).hexdigest() == password
          authentication_success = True
          groups = []
          if authentication_success:
            groups = ['admin',]
        else:
          try:
            authentication_success, groups = erp5.ERP5Site_authenticatePaloUser(
                                                  login, password)
          except (xmlrpclib.Fault, socket.error), e:
            logger.exception(e)
            authentication_success = 'FALSE'
            groups = []

        result = authentication_success and "TRUE" or "FALSE"
        if not authentication_success:
          logger.info("Wrong login from %r" % (login, ))
        output('LOGIN;%s' % result)
        logger.info("Authenticated user %r with groups %r" % (login, groups))
        output(";".join(['GROUPS'] + groups))
      elif cmd == 'USER LOGOUT':
        logger.debug("USER LOGOUT %s" % args)
      else:
        logger.warning("Unhandled command %s with args:%s" % (cmd, args))
      output('DONE')
    except:
      logger.critical("Error occured", exc_info=True)
      raise

if __name__ == '__main__':
  main()

