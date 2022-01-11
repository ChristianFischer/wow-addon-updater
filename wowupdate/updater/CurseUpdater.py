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
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from wowupdate.updater.Updater import IUpdater
from wowupdate.updater.Updater import DownloadableWrapper
from wowupdate.updater.ZipInstaller import downloadZipFromResponse
from wowupdate.updater.ZipInstaller import ZipDownloadable


regex_download_links = [
	re.compile('<a\\s+class="download__link"\\s+href="(/.*?/file)">'),
	re.compile('Elerium.PublicProjectDownload.countdown\\("(/.*?/file)"\\);')
]


class CurseUpdater(IUpdater):

	# ID for WoW in the curse repository
	GAME_ID_WOW = 1

	# flavor for retail wow (unlike classic)
	GAME_FLAVOR_WOW_RETAIL = 'wow_retail'

	FILE_TYPE_RELEASE = 1
	FILE_TYPE_BETA    = 2
	FILE_TYPE_ALPHA   = 3

	def canHandle(self, addon):
		if addon.toc.curse_project_id is None:
			return False

		#if addon.toc.curse_version is None:
		#	return False

		return True


	def findUpdateFor(self, addon):
		project_id = addon.toc.curse_project_id

		if project_id.isdecimal():
			# when project id is numeric, we can query the API for the id
			return self.findDownloadById(project_id, addon.name)
		else:
			# for non-numeric IDs we try to search and match to the 'slug' entry
			return self.findDownloadBySearchQuery(
					project_id,
					selector=lambda json_data: json_data['slug'] == project_id
			)


	def findDownloadByName(self, addon_name):
		return self.findDownloadBySearchQuery(
				addon_name,
				selector=lambda json_data: json_data['name'] == addon_name or json_data['slug'] == addon_name
		)


	def findDownloadBySearchQuery(self, query, selector):
		escaped_query = urllib.parse.quote(query)
		url = ('https://addons-ecs.forgesvc.net/api/v2/addon/search?gameId=%i&pageSize=25&searchFilter=%s' % (self.GAME_ID_WOW, escaped_query))

		try:
			with self.httpget(url) as response:
				text = self.readTextFromResponse(response)
				json_data = json.loads(text)

				for addon_json_data in json_data:
					if selector(addon_json_data):
						downloadable = self.createDownloadableFromJsonData(addon_json_data)

						return downloadable

				return None

		except urllib.error.HTTPError as exc:
			raise exc


	def findDownloadById(self, addon_id, addon_name):
		url = ('https://addons-ecs.forgesvc.net/api/v2/addon/%s' % urllib.parse.quote(addon_id))

		try:
			with self.httpget(url) as response:
				text = self.readTextFromResponse(response)
				json_data = json.loads(text)

				return self.createDownloadableFromJsonData(json_data)

		except urllib.error.HTTPError as exc:
			raise exc


	def createDownloadableFromJsonData(self, json_data):
		selected_file_id = 0
		selected_file = None

		for v in json_data['gameVersionLatestFiles']:
			if v['gameVersionFlavor'] != self.GAME_FLAVOR_WOW_RETAIL:
				continue

			if v['fileType'] != self.FILE_TYPE_RELEASE:
				continue

			selected_file_id = max(selected_file_id, v['projectFileId'])

		if selected_file_id != 0:
			for v in json_data['latestFiles']:
				if v['id'] == selected_file_id:
					selected_file = v

		if selected_file is not None:
			file_url = selected_file['downloadUrl']

			downloadable = ZipDownloadable(url=file_url)
			downloadable.name = json_data['name']
			downloadable.version = selected_file['displayName']

			return downloadable


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
			'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0',
			'Accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
			'Accept-Charset':            'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
			'Accept-Encoding':           'gzip, deflate, br',
			'Connection':                'keep-alive',
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


	def readTextFromResponse(self, response):
		data = response.read()

		if len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b:
			gz = gzip.GzipFile(fileobj=io.BytesIO(data))
			data = gz.read()

		text = data.decode('UTF-8')

		return text


	def createDownloadableFromDownloadPageResponse(self, addon_id, addon_name, response):
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


