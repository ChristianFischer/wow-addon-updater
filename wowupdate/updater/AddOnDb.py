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

import io
import json
import os

from wowupdate.updater.AddOn import AddOn
from wowupdate.updater.AddOn import Toc


addondb_filename = 'addons.db.json'


class AddOnDb:
	def __init__(self, addons_dir):
		self.addons_dir = addons_dir
		self.dirty = False
		self.addons = {}


	def clear(self):
		self.addons = {}
		self.dirty = True


	def add(self, addon):
		self.addons[addon.name] = addon
		self.dirty = True


	def getAddons(self):
		addons = []

		for addon in self.addons.values():
			addons += [addon]

		return addons


	def isFolderKnown(self, folder):
		for addon in self.addons.values():
			if folder in addon.folders:
				return True

		return False


	def open(self):
		with io.open(os.path.join(self.addons_dir, addondb_filename), 'r') as input:
			data = json.load(input)

			for key in data:
				addon_data = data[key]

				addon = AddOn.parse(self.addons_dir, key)
				toc = None

				if addon is not None:
					toc = addon.toc
				else:
					addon = AddOn(None, key)
					toc = Toc()

				if 'folders' in addon_data:
					for folder in addon_data['folders']:
						addon.folders.add(folder)

				if 'curse_project_id' in addon_data:
					toc.curse_project_id = addon_data['curse_project_id']

				if 'version' in addon_data:
					toc.curse_version = None
					toc.version = addon_data['version']

				addon.updateToc(toc)

				self.addons[key] = addon

			self.dirty = False

			return True

		return False


	def save(self):
		json_data = {}

		for key in self.addons:
			addon = self.addons[key]
			json_data[key] = addon.to_json()

		#bytes = io.BytesIO()
		#json.dump(json_data, bytes, sort_keys=True, indent=2)

		with io.open(os.path.join(self.addons_dir, addondb_filename), 'w') as output:
			#output.write(bytes)
			json.dump(json_data, output, sort_keys=True, indent=2)

			self.dirty = False
