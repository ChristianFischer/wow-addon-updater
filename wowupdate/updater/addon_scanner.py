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

from builtins import len
from builtins import range

from wowupdate.updater.colors import *

from wowupdate.updater.AddOn import AddOn



pattern_dir = re.compile("(.*?)/.*")




def update_all(addondb, config, dry_run=False, scan_all=True):
	# get the list of all known addons
	addons = addondb.getAddons()

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
	addons.sort(key=lambda addon: addon.name.lower())

	for addon in addons:
		addon_color = NO_COLOR
		status_color = NO_COLOR
		status = ""

		downloadable = findUpdateFor(addon, config)
		installable = None

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

		print("%s%-55s%s%25s%s" % (addon_color, addon.to_string(), status_color, status, NO_COLOR))

		if not dry_run:
			if installable is not None:
				if addon.isVersionUpgrade(installable.version):
					if installable.source is not None:
						print("  installing %s" % installable.source)

					installable.install(config.addons_dir)
					installable.updateAddonInfo(addon)

					# store downloaded addon into addondb
					addondb.add(addon)

					print("%sDONE%s" % (GREEN, NO_COLOR))

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

