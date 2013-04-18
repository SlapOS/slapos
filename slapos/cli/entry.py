#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys

import cliff
import cliff.app
import cliff.commandmanager

import slapos.version


class SlapOSCommandManager(cliff.commandmanager.CommandManager):
    def find_command(self, argv):
        # XXX a little cheating, 'slapos node' is not documented
        #     by the help command
        if argv == ['node']:
            argv = ['node', 'status']

        return super(SlapOSCommandManager, self).find_command(argv)


class SlapOSApp(cliff.app.App):

    log = logging.getLogger(__name__)

    def __init__(self):
        super(SlapOSApp, self).__init__(
            description='SlapOS client',
            version=slapos.version.version,
            command_manager=SlapOSCommandManager('slapos.cli'),
        )

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    app = SlapOSApp()
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
