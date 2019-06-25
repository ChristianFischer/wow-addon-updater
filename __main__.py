# Copyright (C) 2018 by Christian Fischer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import sys

from wowupdate.updater.Config import Config
from wowupdate.updater.AddOnDb import AddOnDb
from wowupdate.updater.addon_scanner import update_all



addons_dir = os.path.join(os.getcwd(), '_retail_', 'Interface', 'AddOns')


config = Config()
config.addons_dir = addons_dir


# read addondb
addondb = AddOnDb(config)
addondb.open()



def cmd_shell(arg):
	parser = make_parser_shell()

	for line in sys.stdin:
		result = parser.parse_args(line.strip().split())

		print("### %s" % result)

		if 'shell_exit' in result and result.shell_exit:
			break

		result.run(result)


def cmd_update(arg):
	update_all(addondb=addondb, config=config, dry_run=arg.dry)


def cmd_install(arg):
	print("installing %s" % arg.ADDON_ID)


def cmd_remove(arg):
	print("removing %s" % arg.ADDON_ID)


def make_parser():
	# main parser
	parser = argparse.ArgumentParser(
		description="Update and Installer script for WoW addons"
	)

	parser.add_argument(
		"--dry",
		action="store_true"
	)

	# subparsers
	subparsers = parser.add_subparsers()

	# help
	parser_help = subparsers.add_parser("help")
	parser_help.set_defaults(run=lambda args: parser.print_help())


	# updateall
	parser_updateall = subparsers.add_parser("update")
	parser_updateall.set_defaults(run=cmd_update)


	# install
	parser_install = subparsers.add_parser("install")

	parser_install.add_argument(
		"ADDON_ID",
		action="store",
	)

	parser_install.set_defaults(run=cmd_install)

	return parser, subparsers


def make_parser_cl():
	parser, subparsers = make_parser()

	# shell
	parser_shell = subparsers.add_parser("shell")
	parser_shell.set_defaults(run=cmd_shell)

	return parser


def make_parser_shell():
	parser, subparsers = make_parser()

	# exit
	parser_shell = subparsers.add_parser("exit")
	parser_shell.set_defaults(shell_exit=True)

	return parser


parser = make_parser_cl()
result = parser.parse_args()
result.run(result)

exit()
