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
import urllib.request

from zipfile import ZipFile

from builtins import AttributeError
from builtins import Exception

from wowupdate.updater.AddOn import Toc
from wowupdate.updater.Updater import IDownloadable
from wowupdate.updater.Updater import IInstallable


class ZipInstallable(IInstallable):

	def __init__(self, zipfl, root_dir=None):
		IInstallable.__init__(self)
		self.zipfl = zipfl
		self.subdir_prefix = ''
		self.toc = None

		if root_dir is not None:
			self.subdir_prefix = root_dir + '/'


	def parseZipInfo(self):
		self.folders.clear()

		pattern_dir = re.compile("%s(.*?)/.*" % self.subdir_prefix)

		for info in self.zipfl.infolist():
			m = pattern_dir.match(info.filename)
			if m is not None:
				folder = m.group(1).strip()

				if folder != "" and not folder.startswith('.'):
					self.folders.add(folder)


	def install(self, addons_dir):
		if not os.path.exists(addons_dir):
			raise AttributeError("addons_dir does not exist: %s" % addons_dir)

		for root_dir in self.folders:
			path = os.path.join(addons_dir, root_dir)

			while os.path.exists(path):
				shutil.rmtree(path)

				# some delay to ensure the directory is deleted
				time.sleep(0.100)

			if os.path.exists(path):
				raise Exception("path %s was not deleted." % path)

		# some delay to ensure the directory is deleted
		time.sleep(0.100)

		# self.zipfl.extractall(addons_dir)

		for info in self.zipfl.infolist():
			for folder in self.folders:
				folder_path = self.subdir_prefix + folder + '/'
				if info.filename.startswith(folder_path):
					file_path = os.path.relpath(info.filename, folder_path)
					src_file = self.zipfl.open(info)
					dst_path = os.path.join(addons_dir, folder, file_path)

					if ".." in dst_path:
						print("lala")
						pass

					if info.is_dir():
						os.makedirs(dst_path, exist_ok=False)
					else:
						parent_path = os.path.dirname(dst_path)
						os.makedirs(parent_path, exist_ok=True)

						with io.open(dst_path, 'wb') as dst_file:
							shutil.copyfileobj(src_file, dst_file)
							dst_file.close()

		self.zipfl.close()


	def updateAddonInfo(self, addon):
		#addon.updateToc(self.toc)
		addon.folders = self.folders
		addon.version = self.version


	def findFileInZip(self, file):
		lower_filename = (self.subdir_prefix + file).lower()

		for fileinfo in self.zipfl.infolist():
			if fileinfo.filename.lower() == lower_filename:
				return fileinfo

		return None



def downloadZipFromResponse(response, name=None, source=None, version=None, zip_root=None):
	zipdata_bytes = response.read()
	zipdata = io.BytesIO(zipdata_bytes)

	zipfl = ZipFile(zipdata, 'r')

	installable = ZipInstallable(zipfl, root_dir=zip_root)
	installable.parseZipInfo()
	installable.source  = source
	installable.version = version

	if name is not None:
		toc_file_name = name + '/' + name + '.toc'
		toc_file_info = installable.findFileInZip(toc_file_name)

		if toc_file_info is not None:
			with zipfl.open(toc_file_info, 'r') as toc_file:
				data = toc_file.read()
				toc_file_str = data.decode('utf-8').splitlines()
				toc = Toc.parseFileData(toc_file_str)

				if toc.version is not None:
					installable.version = toc.version

				installable.toc = toc

	return installable




class ZipDownloadable(IDownloadable):
	def __init__(self, url=None, response=None):
		IDownloadable.__init__(self)
		self.name     = None
		self.url      = url
		self.response = response

	def download(self):
		if self.response is not None:
			return downloadZipFromResponse(
				self.response,
				source=self.url,
				name=self.name,
				version=self.version
			)

		if self.url is not None:
			with urllib.request.urlopen(self.url) as response:
				return downloadZipFromResponse(
					response,
					source=self.url,
					name=self.name,
					version=self.version
				)

		return None
