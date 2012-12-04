# -*- coding: utf-8 -*-

import logging
import Queue
import socket
import thread
import time

import slapos.recipe.addresiliency.renamer
import slapos

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


BASE_PORT = 50000
SLEEPING_MINS = 2           # XXX was 30, increase after testing

MSG_PING = 'ping'
MSG_HALT = 'halt'
MSG_VICTORY = 'victory'

MSG_OK = 'ok'

STATE_NORMAL = 'normal'
STATE_WAITINGCONFIRM = 'waitingConfirm'
STATE_ELECTION = 'election'
STATE_REORGANIZATION = 'reorganization'



## Leader is always number 0

class ResilientInstance(object):

    def __init__(self, comm, renamer, confpath):
        self.comm = comm
        self.participant_id = 0
        self.state = STATE_NORMAL
        self.halter_id = 0
        self.inElection = False
        self.alive = True

        self.mainCanal = self.comm.create_canal([MSG_PING, MSG_HALT, MSG_VICTORY])

        self.renamer = renamer
        self.okCanal = self.comm.create_canal([MSG_OK])
        self.confpath = confpath
        self.loadConnectionInfo()

    def loadConnectionInfo(self):
        params = open(self.confpath, 'r').readlines()
        self.total_participants = len(params[0].split())
        new_id = int(params[1])
        if self.participant_id != new_id:
            self.halter_id = new_id
            self.participant_id = new_id 
        log.debug('I am {} of {}'.format(self.participant_id, self.total_participants))

    ## Needs to be changed to use the master
    def aliveManagement(self):
        while self.alive:
            log.info('XXX sleeping for %d minutes' % SLEEPING_MINS)
            time.sleep(SLEEPING_MINS*60)
            if self.participant_id == 0:
                continue
            self.comm.send(MSG_PING, 0)
            message, sender = self.okCanal.get()
            if message:
                continue
            self.election()

    def listen(self):
        while self.alive:
            self.comm.recv()

    def main(self):
        while self.alive:
            message, sender = self.mainCanal.get()
            if message == MSG_PING:
                self.comm.send(MSG_OK, sender)

            elif message == MSG_HALT:
                self.state = STATE_WAITINGCONFIRM
                self.halter_id = int(sender)
                self.comm.send(MSG_OK, sender)

            elif message == MSG_VICTORY:
                if int(sender) == self.halter_id and self.state == STATE_WAITINGCONFIRM:
                    log.info('{} thinks {} is the leader'.format(self.participant_id, sender))
                    self.comm.send(MSG_OK, sender)
                self.state = STATE_NORMAL

    def election(self):
        self.inElection = True
        self.loadConnectionInfo()
        # Check if I'm the highest instance alive
        for higher in range(self.participant_id + 1, self.total_participants):
            self.comm.send(MSG_PING, higher)
            message, sender = self.okCanal.get()
            if message:
                log.info('{} is alive ({})'.format(higher, self.participant_id))
                self.inElection = False
                return False
            continue

        if not self.alive:
            return False

        # I should be the new coordinator, halt those below me
        log.info('Should be ME : {}'.format(self.participant_id))
        self.state = STATE_ELECTION
        self.halter_id = self.participant_id
        ups = []
        for lower in range(self.participant_id):
            self.comm.send(MSG_HALT, lower)
            message, sender = self.okCanal.get()
            if message:
                ups.append(lower)

        #Broadcast Victory
        self.state = STATE_REORGANIZATION
        for up in ups:
            self.comm.send(MSG_VICTORY, up)
            message, sender = self.okCanal.get()
            if message:
                continue
            log.info('Something is wrong... let\'s start over')
            return self.election()
        self.state = STATE_NORMAL
        self.active = True
        log.info('{} Is THE LEADER'.format(self.participant_id))

        self.renamer.failover()

        self.inElection = False

        return True



class FilteredCanal(object):

    def __init__(self, accept, timeout):
        self.accept = accept
        self.queue = Queue.Queue()
        self.timeout = timeout

    def append(self, message, sender):
        if message in self.accept:
            self.queue.put([message, sender])

    def get(self):
        try:
            return self.queue.get(timeout=self.timeout)
        except Queue.Empty:
            return [None, None]



class Wrapper(object):

    def __init__(self, confpath, timeout=20):
        self.canals = []
        self.ips = []
        self.participant_id = 0
        self.timeout = timeout
        self.confpath = confpath
        self.getConnectionInfo()
        self.socket = None

    def getConnectionInfo(self):
        params = open(self.confpath, 'r').readlines()
        self.ips = params[0].split()
        self.participant_id = int(params[1])
        log.debug('I am {} of {}'.format(self.participant_id, self.ips))

    def start(self):
        self.getConnectionInfo()
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.socket.bind((self.ips[self.participant_id], BASE_PORT + self.participant_id))
        self.socket.listen(5)

    def send(self, message, number):
        self.getConnectionInfo()
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            s.connect((self.ips[number], BASE_PORT + number))
            s.send(message + (' {}\n'.format(self.participant_id)))
        except (socket.error, socket.herror, socket.gaierror, socket.timeout):
            pass
        finally:
            s.close()

    def create_canal(self, accept):
        created = FilteredCanal(accept, self.timeout)
        self.canals.append(created)
        return created

    def recv(self):
        client, _ = self.socket.accept()
        client_message = client.recv(1024)
        if client_message:
            message, sender = client_message.split()
            for canal in self.canals:
                canal.append(message, int(sender))




def run(args):
    confpath = args.pop('confpath')

    renamer = slapos.recipe.addresiliency.renamer.Renamer(server_url = args.pop('server_url'),
                                                          key_file = args.pop('key_file'),
                                                          cert_file = args.pop('cert_file'),
                                                          computer_guid = args.pop('computer_id'),
                                                          partition_id = args.pop('partition_id'),
                                                          software_release = args.pop('software'),
                                                          namebase = args.pop('namebase'))

    if args:
        raise ValueError('Unknown arguments: %s' % ', '.join(args))

    wrapper = Wrapper(confpath=confpath, timeout=20)

    computer = ResilientInstance(wrapper, renamer=renamer, confpath=confpath)

    # idle waiting for connection infos
    while computer.total_participants < 2:
        computer.loadConnectionInfo()
        time.sleep(30)

    log.info('Starting')

    computer.comm.start()
    thread.start_new_thread(computer.listen, ())
    thread.start_new_thread(computer.aliveManagement, ())

    computer.main()

