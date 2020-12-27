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

import os
import re
import urllib.error

from builtins import *
from time import time

from wowupdate.updater.colors import *

from wowupdate.updater.AddOn import AddOn



pattern_dir = re.compile("(.*?)/.*")



def get_update_generation(addon):
	last_updated = addon.last_updated
	now = time()
	age = max(0, now - last_updated)

	# convert into hours
	age /= 3600.0

	# never updated
	if last_updated == 0:
		return 9

	# last hour
	if age < 1:
		return 0

	# less than 16h (likely the same day)
	if age < 16:
		return 1

	# less than 48h (recently updated)
	if age < 48:
		return 2

	# within the last 7 days
	if age < (7 * 24):
		return 3

	# long time not updated
	return 8



def update_all(addondb, config, dry_run=False, scan_all=True):
	# get the list of all known addons
	addons = addondb.getAddons()

	# store a list of updated addons
	addons_updated = []

	# if enabled, search for currently unknown addons
	if scan_all:
		for subdir in os.listdir(config.addons_dir):
			addonpath = os.path.join(config.addons_dir, subdir)

			# check if this folder is already known by ano other addon
			if addondb.isFolderKnown(subdir):
				continue

			try:
				# read the addon's metadata
				addon = AddOn.parse(addonpath, subdir)

				if addon is not None:
					addons += [addon]

			except:
				print("%serror reading folder %s%s" % (RED, subdir, NO_COLOR))

	# find addons, which are part of another addon package and remove them
	for addon_index in range(len(addons) - 1, 0, -1):
		addon = addons[addon_index]

		for maybe_parent in addons:
			if addon.dependsOn(maybe_parent):
				addons.remove(addon)
				break

	# sort by addon name (case insensitive)
	# and their time last updated
	addons.sort(key=lambda addon: (get_update_generation(addon), addon.name.lower()))

	for addon in addons:
		addon_color = NO_COLOR
		status_color = NO_COLOR
		status = ""

		installable = None

		try:
			downloadable = findUpdateFor(addon, config)

			if downloadable is not None:
				status = downloadable.version
				status_color = GRAY

				if addon.isVersionUpgrade(downloadable.version):
					installable = downloadable.download()

					if installable is not None:
						if addon.isVersionUpgrade(installable.version):
							if addon.ignore_updates:
								status = "[ign] %s" % installable.version
								status_color = YELLOW
								installable = None
							else:
								status = "=> %s" % installable.version
								status_color = GREEN
			else:
				addon_color = GRAY

		except urllib.error.HTTPError as exc:
			status = ("%d: %s" % (exc.code, exc.msg))
			status_color = RED

		except BaseException as exc:
			status = exc
			status_color = RED

		print("%s%-55s%s%25s%s" % (addon_color, addon.to_string(), status_color, status, NO_COLOR))

		if not dry_run:
			if installable is not None:
				if addon.isVersionUpgrade(installable.version):
					if installable.source is not None:
						print("  installing %s" % installable.source)

					old_version = addon.version

					installable.install(config.addons_dir)
					installable.updateAddonInfo(addon)

					# update timestamp
					addon.last_updated = int(time())

					# store downloaded addon into addondb
					addondb.add(addon)

					# store information of this update
					addons_updated.append(
						{
							'addon': addon,
							'from':  old_version,
							'to':    installable.version,
						}
					)

					print("%sDONE%s" % (GREEN, NO_COLOR))

	if len(addons_updated) > 0:
		print("")
		print("%sSummary:%s" % (MAGENTA, NO_COLOR))

		for updated in addons_updated:
			addon        = updated['addon']
			version_from = updated['from']
			version_to   = updated['to']

			str_addon    = addon.name
			str_version  = ('%s => %s' % (version_from, version_to))
			str_space    = (80 - len(str_addon) - len(str_version)) * ' '

			print(
				"%s%s%s%s%s" % (
					MAGENTA,
					str_addon,
					str_space,
					str_version,
					NO_COLOR
				)
			)

	if addondb.dirty:
		addondb.save()


def findUpdateFor(addon, config):
	for updater in config.updaters:
		if updater.isPreferredUpdaterFor(addon):
			update = updater.findUpdateFor(addon)

			if update is not None:
				return update

	for updater in config.updaters:
		if updater.canHandle(addon):
			update = updater.findUpdateFor(addon)

			if update is not None:
				return update

	for updater in config.updaters:
		update = updater.findDownloadByName(addon.name)

		if update is not None:
			return update

	return None

