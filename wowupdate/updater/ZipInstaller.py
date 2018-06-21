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
import os
import re
import shutil
import time

from zipfile import ZipFile

from builtins import AttributeError
from builtins import Exception
from builtins import set

from wowupdate.updater.AddOn import Toc
from wowupdate.updater.Updater import IDownloadable
from wowupdate.updater.Updater import IInstallable


pattern_dir = re.compile("(.*?)/.*")



class ZipInstallable(IInstallable):

	def __init__(self, zipfl):
		IInstallable.__init__(self)
		self.zipfl = zipfl


	def install(self, addons_dir):
		if not os.path.exists(addons_dir):
			raise AttributeError("addons_dir does not exist: %s" % addons_dir)

		root_dirs = set()

		for info in self.zipfl.infolist():
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

		self.zipfl.extractall(addons_dir)

		self.zipfl.close()



def findFileInZip(zipfl, file):
	lower_filename = file.lower()

	for fileinfo in zipfl.infolist():
		if fileinfo.filename.lower() == lower_filename:
			return fileinfo

	return None



def downloadZipFromResponse(response, name=None, source=None, version=None):
	zipdata_bytes = response.read()
	zipdata = io.BytesIO(zipdata_bytes)

	with ZipFile(zipdata, 'r') as zipfl:
		installable = ZipInstallable(zipfl)
		installable.source  = source
		installable.version = version

		if name is not None:
			toc_file_name = name + '/' + name + '.toc'
			toc_file_info = findFileInZip(zipfl, toc_file_name)

			if toc_file_info is not None:
				with zipfl.open(toc_file_info, 'r') as toc_file:
					data = toc_file.read()
					toc_file_str = data.decode('utf-8').splitlines()
					toc = Toc.parseFileData(toc_file_str)

					if toc.version is not None:
						installable.version = toc.version

		return installable

	return None




class ZipDownloadable(IDownloadable):
	def __init__(self, response):
		IDownloadable.__init__(self)
		self.name     = None
		self.response = response

	def download(self):
		return downloadZipFromResponse(
			self.response,
			source=self.url,
			name=self.name,
			version=self.version
		)
