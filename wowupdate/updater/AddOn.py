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

import codecs
import os
import re

from builtins import set


regex_toc_attr = re.compile('## (.+?):\s*(.+)')


class Toc:
	@staticmethod
	def parseFile(file):
		try:
			with codecs.open(file, encoding='utf-8') as fp:
				return Toc.parseFileData(fp)

		except:
			pass

		return None


	@staticmethod
	def parseFileData(filedata):
		toc = Toc()

		version = None
		version_curse = None

		for line in filedata:
			m = regex_toc_attr.match(line)
			if m is not None:
				key = m.group(1).strip()
				val = m.group(2).strip()

				if key == 'Version':
					version = val

				if key == 'Dependencies':
					toc.dependencies = re.split(",\s*", val)

				if key == 'X-Curse-Packaged-Version':
					toc.curse_version = val
					version_curse = val

				if key == 'X-Curse-Project-ID':
					toc.curse_project_id = val

				if key == 'X-Website':
					toc.website_url = val

		if version is not None:
			toc.version = version
		elif version_curse is not None:
			toc.version = version_curse

		return toc


	def __init__(self):
		self.version			= None
		self.dependencies		= []

		self.curse_version		= None
		self.curse_project_id	= None
		self.website_url		= None




class AddOn:
	@staticmethod
	def parse(path, name):
		toc = Toc.parseFile(os.path.join(path, name+'.toc'))

		if toc is not None:
			addon = AddOn(path, name)
			addon.updateToc(toc)

			return addon

		return None


	def __init__(self, path, name):
		self.path				= path
		self.name				= name
		self.folders			= set()
		self.toc				= Toc()
		self.last_updated		= 0
		self.ignore_updates		= False

		# add the addon name as a primary folder
		self.folders.add(name)


	def updateToc(self, toc):
		self.toc				= toc
		self.version			= toc.version


	def dependsOn(self, other_addon):
		if other_addon.name in self.toc.dependencies:
			if other_addon.version == self.version:
				if self.name.startswith(other_addon.name):
					return True

		return False


	def isVersionUpgrade(self, version):
		if self.version != version:
			return True

		return False


	def print_details(self):
		print(self.to_string())

		if self.toc.curse_project_id is not None:
			print("  curse project: %s, version %s" % (self.toc.curse_project_id, self.toc.curse_version))

		if self.toc.website_url is not None:
			print("  website: %s" % self.toc.website_url)


	def to_json(self):
		folders = []
		for folder in self.folders:
			folders += [folder]

		folders.sort()

		data = {
			'folders': folders,
			'version': self.version,
		}

		if self.toc.curse_project_id is not None:
			data['curse_project_id'] = self.toc.curse_project_id

		if self.last_updated > 0:
			data['last-updated'] = self.last_updated

		if self.ignore_updates:
			data['ignore-updates'] = self.ignore_updates

		return data


	def to_string(self):
		return "%s (%s)" % (self.name, self.version)


