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
import re
import urllib.error
import urllib.request

from wowupdate.updater.Updater import Updater
from wowupdate.updater.Updater import Update


regex_download_link = re.compile(
	'<a\s+class="download__link"\s+href="(/.*?/file)">'
)


class CurseUpdater(Updater):

	def canHandle(self, addon):
		if addon.curse_project_id is None:
			return False

		if addon.curse_version is None:
			return False

		return True


	def findUpdateFor(self, addon):
		return self.findDownloadById(addon.curse_project_id, addon.name)


	def findDownloadByName(self, addon_name):
		return self.findDownloadById(addon_name.lower(), addon_name)


	def findDownloadById(self, addon_id, addon_name):
		url = ('https://wow.curseforge.com/projects/%s/files/latest' % addon_id)

		try:
			with urllib.request.urlopen(url) as response:
				return self.createUpdateFromResponse(addon_id, addon_name, response)

		except urllib.error.HTTPError:
			pass

		url = ('https://www.curseforge.com/wow/addons/%s/download' % addon_id)

		try:
			with urllib.request.urlopen(url) as response:
				html = response.read().decode('UTF-8')

				m = regex_download_link.search(html)
				if m is not None:
					file_url = m.group(1).strip()
					url = ('https://www.curseforge.com%s' % file_url)

					with urllib.request.urlopen(url) as response2:
						return self.createUpdateFromResponse(addon_id, addon_name, response2)

		except urllib.error.HTTPError:
			pass



	def createUpdateFromResponse(self, addon_id, addon_name, response):
		url = response.url

		pattern_zip_version = re.compile('.*/%s[-+_](.*)\.zip' % addon_name, re.IGNORECASE)
		m = pattern_zip_version.match(url)
		if m is not None:
			zip_version = m.group(1)

			update = Update()
			update.url = url
			update.version = zip_version

			zipdata_bytes = response.read()
			zipdata = io.BytesIO(zipdata_bytes)
			update.zip_data = zipdata

			return update

		return None


