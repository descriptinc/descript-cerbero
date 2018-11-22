# cerbero - a multi-platform build system for Open Source software
# Copyright (C) 2012 Andoni Morales Alastruey <ylatuya@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from cerbero import hacks

try:
    import argparse
except ImportError as e:
    print("Could not import argparse. Try installing it with "\
          "'sudo easy_install argparse")
    raise e

import sys
import errno
import logging
import traceback
import os
import time

from cerbero import config, commands
from cerbero.errors import UsageError, FatalError, BuildStepError, \
    ConfigurationError, CerberoException, AbortedError
from cerbero.utils import _, N_, user_is_root, git
from cerbero.utils import messages as m
from cerbero.utils.manifest import Manifest

description = N_('Build and package a set of modules to distribute them in '
                 'a SDK')

class Main(object):

    def __init__(self, args):
        if user_is_root():
            m.warning(_("Running as root"))

        self.check_in_cerbero_shell()
        self.create_parser()
        self.load_commands()
        self.parse_arguments(args)
        self.self_update()
        self.init_logging()
        self.load_config()
        self.run_command()

    def check_in_cerbero_shell(self):
        if os.environ.get('CERBERO_PREFIX', '') != '':
            self.log_error(_("ERROR: cerbero can't be run "
                             "from a cerbero shell"))

    def log_error(self, msg, print_usage=False, command=None):
        ''' Log an error and exit '''
        if command is not None:
            m.error("***** Error running '%s' command:" % command)
        m.error('%s' % msg)
        if print_usage:
            self.parser.print_usage()
        sys.exit(1)

    def init_logging(self):
        ''' Initialize logging '''
        if self.args.timestamps:
            m.START_TIME = time.monotonic()
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(logging.StreamHandler())

    def create_parser(self):
        ''' Creates the arguments parser '''
        self.parser = argparse.ArgumentParser(description=_(description))
        self.parser.add_argument('-t', '--timestamps', action='store_true', default=False,
                help=_('Print timestamps with every message printed'))
        self.parser.add_argument('-c', '--config', action='append', type=str, default=None,
                help=_('Configuration file used for the build'))
        self.parser.add_argument('-m', '--manifest', action='store', type=str, default=None,
                help=_('Manifest file used to fixate git revisions'))
        if os.path.basename(sys.argv[0]) == 'cerbero-uninstalled':
            self.parser.add_argument('--self-update', action='store', type=str, default=None,
                    help=_('Update cerbero git repository from manifest and exit.'))

    def parse_arguments(self, args):
        ''' Parse the command line arguments '''
        # If no commands, make it show the help by default
        if len(args) == 0:
            args = ["-h"]
        self.args = self.parser.parse_args(args)

    def self_update(self):
        '''Update this instance of cerbero git repository'''

        if not self.args.self_update:
           return

        try:
            manifest = Manifest(self.args.self_update)
            manifest.parse()
            project = manifest.find_project('cerbero')
            git_dir = os.path.dirname(sys.argv[0])
            git.add_remote(git_dir, project.remote, project.fetch_uri)
            git.fetch(git_dir)
            git.checkout(git_dir, project.revision)
        except FatalError as ex:
            self.log_error(_("ERROR: Failed to proceed with self update %s") %
                    ex)
        exit(0)

    def load_commands(self):
        subparsers = self.parser.add_subparsers(help=_('sub-command help'),
                                                dest='command')
        commands.load_commands(subparsers)

    def load_config(self):
        ''' Load the configuration '''
        try:
            self.config = config.Config()
            self.config.load(self.args.config)
            if self.args.manifest:
                self.config.manifest = self.args.manifest
        except ConfigurationError as exc:
            self.log_error(exc, False)

    def run_command(self):
        command = self.args.command
        try:
            res = commands.run(command, self.config, self.args)
        except UsageError as exc:
            self.log_error(exc, True, command)
            sys.exit(1)
        except FatalError as exc:
            traceback.print_exc()
            self.log_error(exc, True, command)
        except BuildStepError as exc:
            self.log_error(exc.msg, False, command)
        except AbortedError as exc:
            self.log_error('', False, command)
        except CerberoException as exc:
            self.log_error(exc, False, command)
        except KeyboardInterrupt:
            self.log_error(_('Interrupted'))
        except IOError as e:
            if e.errno != errno.EPIPE:
                raise
            sys.exit(0)

        if res:
            sys.exit(res)


def main():
    Main(sys.argv[1:])


if __name__ == "__main__":
    main()
