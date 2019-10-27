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

import gzip
import io
import re
import urllib.error
import urllib.request

from wowupdate.updater.Updater import IUpdater
from wowupdate.updater.Updater import DownloadableWrapper
from wowupdate.updater.ZipInstaller import downloadZipFromResponse


regex_download_links = [
	re.compile('<a\s+class="download__link"\s+href="(/.*?/file)">'),
	re.compile('Elerium.PublicProjectDownload.countdown\("(/.*?/file)"\);')
]


class CurseUpdater(IUpdater):

	def canHandle(self, addon):
		if addon.toc.curse_project_id is None:
			return False

		#if addon.toc.curse_version is None:
		#	return False

		return True


	def findUpdateFor(self, addon):
		return self.findDownloadById(addon.toc.curse_project_id, addon.name)


	def findDownloadByName(self, addon_name):
		return self.findDownloadById(addon_name.lower(), addon_name)


	def findDownloadById(self, addon_id, addon_name):
		url1 = ('https://www.curseforge.com/wow/addons/%s/download' % addon_id)

		try:
			with self.httpget(url1) as response:
				data = response.read()

				if len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b:
					gz = gzip.GzipFile(fileobj=io.BytesIO(data))
					data = gz.read()

				html = data.decode('UTF-8')

				for regex_download_link in regex_download_links:
					m = regex_download_link.search(html)
					if m is not None:
						file_url = m.group(1).strip()
						url2 = ('https://www.curseforge.com%s' % file_url)

						with self.httpget(url2, referer=url1) as response2:
							return self.createDownloadableFromResponse(addon_id, addon_name, response2)

		except urllib.error.HTTPError:
			pass


	class CurseRedirectHandler(urllib.request.HTTPRedirectHandler):
		def __init__(self):
			pass

		def redirect_request(self, req, fp, code, msg, headers, newurl):
			referer = req.full_url
			headers['Referer'] = referer

			req = urllib.request.Request(url=newurl, headers=headers)

			return req


	def httpget(self, url, referer=None):
		headers = {
			'Host':                      'www.curseforge.com',
			'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0',
			'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language':           'de,en-US;q=0.7,en;q=0.3',
			'Accept-Encoding':           'gzip, deflate, br',
			'DNT':                       '1',
			'Connection':                'keep-alive',
			'Upgrade-Insecure-Requests': '1',
			'Cache-Control':             'max-age=0',
			'TE':                        'Trailers',
		}

		if referer is not None:
			headers['Referer'] = referer

		redirect_handler = self.CurseRedirectHandler()

		opener = urllib.request.build_opener(redirect_handler)
		urllib.request.install_opener(opener)

		req = urllib.request.Request(url, headers=headers)
		response = urllib.request.urlopen(req)

		urllib.request.install_opener(None)

		return response


	def createDownloadableFromResponse(self, addon_id, addon_name, response):
		url = response.url

		pattern_zip_version = re.compile('.*/%s[-+_]?(.*)\.zip' % addon_name, re.IGNORECASE)
		m = pattern_zip_version.match(url)
		if m is not None:
			zip_version = m.group(1)

			installable = downloadZipFromResponse(
				response,
				source=url,
				name=addon_name,
				version=zip_version
			)

			return DownloadableWrapper(installable)

		return None


