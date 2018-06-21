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

from builtins import Exception


class IDownloadable:
	def __init__(self):
		self.url     = None
		self.version = None

	def download(self):
		raise Exception('Implement me')



class IInstallable:
	def __init__(self):
		self.source  = None
		self.version = None

	def install(self, path):
		raise Exception('Implement me')



class DownloadableWrapper(IDownloadable):
	def __init__(self, installable):
		IDownloadable.__init__(self)
		self.version     = installable.version
		self.installable = installable

	def download(self):
		return self.installable



class IUpdater:

	def canHandle(self, addon):
		return False


	def findUpdateFor(self, addon):
		return None


	def findDownloadByName(self, addon_name):
		return None


