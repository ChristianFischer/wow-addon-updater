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

from wowupdate.updater.colors import *

from wowupdate.updater.AddOn import AddOn
from wowupdate.updater.CurseUpdater import CurseUpdater



pattern_dir = re.compile("(.*?)/.*")


all_updaters = [
	CurseUpdater()
]


def find_addons(path):
	addons_dir = os.path.join(path, 'Interface', 'AddOns')
	dry_run = False

	addons = []
	for subdir in os.listdir(addons_dir):
		addonpath = os.path.join(addons_dir, subdir)

		try:
			addon = AddOn.parse(addonpath, subdir)

			if addon is not None:
				addons += [addon]

		except:
			print("%serror reading folder %s%s" % (RED, subdir, NO_COLOR))

	for addon_index in range(len(addons) - 1, 0, -1):
		addon = addons[addon_index]

		for maybe_parent in addons:
			if addon.dependsOn(maybe_parent):
				addons.remove(addon)
				break

	for addon in addons:
		addon_color = NO_COLOR
		status_color = NO_COLOR
		status = ""

		downloadable = findUpdateFor(addon)
		installable = None

		if downloadable is not None:
			status = downloadable.version
			status_color = GRAY

			if addon.isVersionUpgrade(downloadable.version):
				installable = downloadable.download()

				if installable is not None:
					if addon.isVersionUpgrade(installable.version):
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

					installable.install(addons_dir)

					print("%sDONE%s" % (GREEN, NO_COLOR))


def findUpdateFor(addon):
	for updater in all_updaters:
		if updater.canHandle(addon):
			update = updater.findUpdateFor(addon)

			if update is not None:
				return update

	for updater in all_updaters:
		update = updater.findDownloadByName(addon.name)

		if update is not None:
			return update

	return None

