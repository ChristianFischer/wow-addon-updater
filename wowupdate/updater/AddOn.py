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


regex_toc_attr = re.compile('## (.+?):\s*(.+)')


class AddOn:
	@staticmethod
	def parse(path, name):
		addon = AddOn(path, name)

		version = None
		version_curse = None

		with codecs.open(os.path.join(path, name+'.toc'), encoding='utf-8') as fp:
			for line in fp:
				m = regex_toc_attr.match(line)
				if m is not None:
					key = m.group(1).strip()
					val = m.group(2).strip()

					if key == 'Version':
						version = val

					if key == 'Dependencies':
						addon.dependencies = re.split(",\s*", val)

					if key == 'X-Curse-Packaged-Version':
						addon.curse_version = val
						version_curse = val

					if key == 'X-Curse-Project-ID':
						addon.curse_project_id = val

					if key == 'X-Website':
						addon.website_url = val

		if version is not None:
			addon.version = version
		elif version_curse is not None:
			addon.version = version_curse

		return addon


	def __init__(self, path, name):
		self.path				= path
		self.name				= name
		self.version			= None
		self.dependencies		= []

		self.curse_version		= None
		self.curse_project_id	= None
		self.website_url		= None


	def dependsOn(self, other_addon):
		if other_addon.name in self.dependencies:
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

		if self.curse_project_id is not None:
			print("  curse project: %s, version %s" % (self.curse_project_id, self.curse_version))

		if self.website_url is not None:
			print("  website: %s" % self.website_url)


	def to_string(self):
		return "%s (%s)" % (self.name, self.version)


