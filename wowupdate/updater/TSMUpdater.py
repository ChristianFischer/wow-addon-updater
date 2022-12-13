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

import datetime
import gzip
import hashlib
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from builtins import *
from time import time

from wowupdate.updater.colors import *
from wowupdate.updater.Updater import *



def formatjson(str):
	json_obj = json.loads(str)
	json_str = json.dumps(json_obj, indent=2)
	return json_str



def _decode_private_key(encoded_key):
	return ('').join([hex((int(c, 16) + 7) % 16).lstrip('0x') or '0' for c in encoded_key])


def get_password_salt():
	return _decode_private_key('8b8fa15e9b320e1be7e63f81fe943184')


def get_token_salt():
	return _decode_private_key('f718626e63d8a5697fd36d691b47d005')



class TSMHelper:

	def __init__(self, config):
		self.config      = config
		self.channel     = 'release'
		self.version     = 41200
		self.userdata    = None
		self.session_id  = None
		self.status_data = None


	def log(self, message):
		# print(message)
		pass


	def log_error(self, message):
		print("%s%s%s" % (RED, message, NO_COLOR))


	def getStatusData(self):
		if self.status_data is None:
			status = self.tsm_request('status')

			if status is None:
				self.log_error("Failed to receive status from TSM host")
				return None

			self.log(formatjson(status))
			self.status_data = self.parseJsonResponse(status)

		return self.status_data


	@staticmethod
	def read_last_modified_from(item_data):
		last_modified = 0

		if 'pricingStrings' in item_data:
			pricing_strings = item_data['pricingStrings']

			for key, entry in pricing_strings.items():
				if 'lastModified' in entry:
					item_last_modified = entry['lastModified']
					last_modified = max(last_modified, item_last_modified)

		elif 'lastModified' in item_data:
			item_last_modified = item_data['lastModified']
			last_modified = max(last_modified, item_last_modified)

		return last_modified


	def getLastModifiedTimestamp(self):
		status_data = self.getStatusData()
		last_modified = 0

		if status_data is not None:
			# get region data
			for region in status_data['regions']:
				last_modified = max(last_modified, TSMHelper.read_last_modified_from(region))

			# get realm data
			for realm in status_data['realms']:
				last_modified = max(last_modified, TSMHelper.read_last_modified_from(realm))

		return last_modified


	def getVersionCode(self):
		last_modified = self.getLastModifiedTimestamp()
		timestamp = datetime.datetime.fromtimestamp(last_modified)
		version = timestamp.strftime("%Y%m%d%H%M%S")

		return version



	def tsm_request(self, *args):
		if self.session_id is None:
			success = False
			tsm_config = self.config.getConfig("tsm")

			if tsm_config is not None:
				account  = tsm_config['account']
				password = tsm_config['password']

				success = self.login(account, password)

			if success is False:
				return None

		return self.do_tsm_request(*args)


	def url_request(self, url):
		return self.do_url_request(url)


	def login(self, username, passwd):
		username_hash = hashlib.sha256(bytearray(username, 'UTF-8')).hexdigest()
		passwd_hash_1 = hashlib.sha512(bytearray(passwd,   'UTF-8')).hexdigest()
		passwd_salted = passwd_hash_1 + get_password_salt()
		passwd_hash_2 = hashlib.sha512(bytearray(passwd_salted, 'UTF-8')).hexdigest()

		result = self.do_tsm_request('login', username_hash, passwd_hash_2)

		if result is not None:
			userdata = self.parseJsonResponse(result)

			if userdata is not None:
				if 'session' in userdata:
					self.session_id = userdata['session']
					self.userdata   = userdata

					return True

		return False


	def do_tsm_request(self, *args):
		current_time = int(time())

		token = ('%i:%i:%s' % (self.version, current_time, get_token_salt()))
		token = hashlib.sha256(bytearray(token, 'UTF-8')).hexdigest()

		query_params = {
			'token': token,
			'time':  current_time,
			'version': self.version,
			'channel': self.channel,
		}

		if self.session_id is not None:
			query_params['session'] = self.session_id

		endpoint  = args[0]
		subdomain = 'app-server'

		if self.userdata is not None:
			if endpoint in self.userdata['endpointSubdomains']:
				subdomain = self.userdata['endpointSubdomains'][endpoint]

		url = 'http://%s.tradeskillmaster.com/v2/%s?%s' % (
			subdomain,
			('/'.join(args)),
			urllib.parse.urlencode(query_params),
		)

		result = self.do_url_request(url)

		return result


	def do_url_request(self, url):
		self.log("open url: %s" % url)

		with urllib.request.urlopen(url, ) as response:
			data = response.read()

			# unzip gzipped data, if found
			if len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b:
				bytes = io.BytesIO(data)
				gz    = gzip.GzipFile(fileobj=bytes)
				data  = gz.read()

			# decode
			data = data.decode('UTF-8')

			return data


	def parseJsonResponse(self, json_str):
		json_data = json.loads(json_str, encoding='UTF-8')

		if 'success' in json_data:
			if json_data['success'] == False:
				error = json_data['error']
				self.log_error("Request failed: %s.%s" % error)
				return None

		return json_data



class TSMUpdater(IUpdater):

	def __init__(self, config):
		IUpdater.__init__(self, config)
		self.tsm = TSMHelper(config)


	def isPreferredUpdaterFor(self, addon):
		if addon.name == "TradeSkillMaster_AppHelper":
			return True

		return False


	def findUpdateFor(self, addon):
		if addon.name == "TradeSkillMaster_AppHelper":
			status_data = self.tsm.getStatusData()
			if status_data is not None:
				return TSMAppDataDownloader(self.tsm, status_data, addon)

		return None



class AppData:
	AUCTIONDB_MARKET_DATA = "AUCTIONDB_MARKET_DATA"
	APP_INFO              = "APP_INFO"

	def __init__(self):
		self.content = io.StringIO()


	def add(self, type, realm, data, last_modified):
		self.content.write('select(2, ...).LoadData("%s","%s", [[return ' % (type, realm))
		self.content.write(data)
		self.content.write(']])')
		self.content.write(" --<%s,%s,%s>" % (type, realm, last_modified))
		self.content.write('\n')


	def get_content(self):
		content_str = self.content.getvalue()
		self.content.close()

		return content_str



class TSMAppDataDownloader(IDownloadable):

	API_REALM_ENTRIES = {
		'AUCTIONDB_REALM_DATA':       'data',
		'AUCTIONDB_REALM_SCAN_STAT':  'scanStat',
		'AUCTIONDB_REALM_HISTORICAL': 'historical',
	}

	API_REGION_ENTRIES = {
		'AUCTIONDB_REGION_HISTORICAL': 'historical',
		'AUCTIONDB_REGION_SALE':       'sale',
		'AUCTIONDB_REGION_STAT':       'stat',
		'AUCTIONDB_REGION_COMMODITY':  'commodity'
	}


	def __init__(self, tsm, status_data, appdata_addon):
		IDownloadable.__init__(self)

		self.tsm           = tsm
		self.status_data   = status_data
		self.appdata_addon = appdata_addon
		self.version       = tsm.getVersionCode()


	def download(self):
		status_data = self.status_data
		last_modified = int(time())

		appdata = AppData()

		# get region data
		for region in status_data['regions']:
			name = region['name']
			region_id = region['id']
			region_last_modified = region['lastModified']

			self.tsm.log("update region #%i: %s" % (region_id, name))

			if 'pricingStrings' in region:
				pricing_strings = region['pricingStrings']

				self.download_pricing_strings(
					name,
					region_last_modified,
					appdata,
					pricing_strings,
					TSMAppDataDownloader.API_REGION_ENTRIES
				)

			elif 'downloadUrl' in region:
				download_url = region['downloadUrl']
				data = self.tsm.url_request(download_url)

				appdata.add(AppData.AUCTIONDB_MARKET_DATA, name, data, region_last_modified)

			else:
				data = self.tsm.tsm_request('auctiondb', 'region', str(region_id))
				j = self.tsm.parseJsonResponse(data)
				data = j['data']

				appdata.add(AppData.AUCTIONDB_MARKET_DATA, name, data, region_last_modified)

		# get realm data
		for realm in status_data['realms']:
			name = realm['name']
			realm_id = realm['masterId']
			realm_last_modified = realm['lastModified']

			self.tsm.log("update realm #%i: %s" % (realm_id, name))

			if 'pricingStrings' in realm:
				pricing_strings = realm['pricingStrings']

				self.download_pricing_strings(
					name,
					realm_last_modified,
					appdata,
					pricing_strings,
					TSMAppDataDownloader.API_REALM_ENTRIES
				)

			elif 'downloadUrl' in realm:
				download_url = realm['downloadUrl']
				data = self.tsm.url_request(download_url)

				appdata.add(AppData.AUCTIONDB_MARKET_DATA, name, data, realm_last_modified)

			else:
				data = self.tsm.tsm_request('auctiondb', 'realm', str(realm_id))
				j = self.tsm.parseJsonResponse(data)
				data = j['data']

				appdata.add(AppData.AUCTIONDB_MARKET_DATA, name, data, realm_last_modified)

		appdata.add(
			AppData.APP_INFO,
			"Global",
			'{version=%i,lastSync=%i,addonVersions={},message={id=0,msg=""},news=%s}' % (
				self.tsm.version,
				last_modified,
				status_data['addonNews']
			),
			last_modified
		)

		appdata_content = appdata.get_content()

		return TSMAppDataInstallable(appdata_content, self.version)


	def download_pricing_strings(self, name, last_modified, appdata, pricing_strings, entries):
		for api_type, key in entries.items():
			if key in pricing_strings:
				pricing_string = pricing_strings[key]

				if 'lastModified' in pricing_string:
					item_last_modified = pricing_string['lastModified']
				else:
					item_last_modified = last_modified

				if 'url' in pricing_string:
					download_url = pricing_string['url']
					data = self.tsm.url_request(download_url)

					appdata.add(api_type, name, data, item_last_modified)



class TSMAppDataInstallable(IInstallable):
	def __init__(self, appdata_content, version):
		IInstallable.__init__(self)

		self.appdata_content = appdata_content
		self.version         = version


	def install(self, path):
		out = io.open(os.path.join(path, 'TradeSkillMaster_AppHelper', 'AppData.lua'), 'w')
		out.write(self.appdata_content)
		out.close()


	def updateAddonInfo(self, addon):
		addon.version = self.version
