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
import shutil
import time

from zipfile import ZipFile

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

		update = findUpdateFor(addon)

		if update is not None:
			status = update.version
			status_color = GRAY

			if addon.isVersionUpgrade(update.version):
				if update.zip_data is not None:
					status = "=> %s" % update.version
					status_color = GREEN
		else:
			addon_color = GRAY

		print("%s%-55s%s%25s%s" % (addon_color, addon.to_string(), status_color, status, NO_COLOR))

		if not dry_run:
			if update is not None:
				if addon.isVersionUpgrade(update.version):
					if update.zip_data is not None:
						if update.url is not None:
							print("  installing %s" % update.url)

						installZipData(update.zip_data, addons_dir)

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





def installZipData(zipdata, addons_dir):
	if not os.path.exists(addons_dir):
		raise AttributeError("addons_dir does not exist: %s" % addons_dir)

	with ZipFile(zipdata, 'r') as zipfl:
		root_dirs = set()

		for info in zipfl.infolist():
			m = pattern_dir.match(info.filename)
			if m is not None:
				root_dir = m.group(1).strip()

				if root_dir != "":
					root_dirs.add(root_dir)

		for root_dir in root_dirs:
			path = os.path.join(addons_dir, root_dir)
			if os.path.exists(path):
				shutil.rmtree(path)

			if os.path.exists(path):
				raise Exception("path %s was not deleted." % path)

		# some delay to ensure the directory is deleted
		time.sleep(0.100)

		zipfl.extractall(addons_dir)

		zipfl.close()

