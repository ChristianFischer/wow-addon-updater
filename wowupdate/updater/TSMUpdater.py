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
		self.version     = 400
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


	def getLastModifiedTimestamp(self):
		status_data = self.getStatusData()
		last_modified = 0

		if status_data is not None:
			# get region data
			for region in status_data['regions']:
				region_last_modified = region['lastModified']

				if region_last_modified > last_modified:
					last_modified = region_last_modified

			# get realm data
			for realm in status_data['realms']:
				realm_last_modified = realm['lastModified']

				if realm_last_modified > last_modified:
					last_modified = realm_last_modified

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




class TSMAppDataDownloader(IDownloadable):

	def __init__(self, tsm, status_data, appdata_addon):
		IDownloadable.__init__(self)

		self.tsm           = tsm
		self.status_data   = status_data
		self.appdata_addon = appdata_addon
		self.version       = tsm.getVersionCode()


	def download(self):
		status_data = self.status_data
		last_modified = int(time())

		out = io.StringIO()

		# get region data
		for region in status_data['regions']:
			name = region['name']
			region_id = region['id']
			region_last_modified = region['lastModified']

			self.tsm.log("update region #%i: %s" % (region_id, name))

			if 'downloadUrl' in region:
				download_url = region['downloadUrl']
				data = self.tsm.url_request(download_url)
			else:
				data = self.tsm.tsm_request('auctiondb', 'region', str(region_id))
				j = self.tsm.parseJsonResponse(data)
				data = j['data']

			out.write('select(2, ...).LoadData("AUCTIONDB_MARKET_DATA","%s", [[return ' % name)
			out.write(data)
			out.write(']])')
			out.write('\n')

		# get realm data
		for realm in status_data['realms']:
			name = realm['name']
			realm_id = realm['masterId']
			realm_last_modified = realm['lastModified']

			self.tsm.log("update realm #%i: %s" % (realm_id, name))

			if 'downloadUrl' in realm:
				download_url = realm['downloadUrl']
				data = self.tsm.url_request(download_url)
			else:
				data = self.tsm.tsm_request('auctiondb', 'realm', str(realm_id))
				j = self.tsm.parseJsonResponse(data)
				data = j['data']

			out.write('select(2, ...).LoadData("AUCTIONDB_MARKET_DATA","%s",[[return ' % name)
			out.write(data)
			out.write(']])')
			out.write('\n')

		out.write('select(2, ...).LoadData("APP_INFO","Global",[[return {')
		out.write('version=%i,lastSync=%i,addonVersions={},message={id=0,msg=""},' % (self.tsm.version, last_modified))
		out.write('news=%s' % status_data['addonNews'])
		out.write('}]])')

		appdata_content = out.getvalue()

		out.close()

		return TSMAppDataInstallable(appdata_content, self.version)



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
