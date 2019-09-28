#  Copyright (C) 2019 by Christian Fischer
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
#
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

import re
import urllib.error
import urllib.request

from wowupdate.updater.Updater import IUpdater
from wowupdate.updater.Updater import DownloadableWrapper
from wowupdate.updater.ZipInstaller import downloadZipFromResponse


regex_github_url = re.compile('^https://github.com/(.*?)/(.*?)/?$')


class GithubUpdater(IUpdater):

	def canHandle(self, addon):
		if addon.toc.git_url is not None:
			return True

		return False


	def findUpdateFor(self, addon):
		if addon.toc.git_url is not None:
			return self.findDownloadByGitRepo(addon.name, addon.toc.git_url)

		return None


	def findDownloadByName(self, addon_name):
		return None


	def findDownloadByGitRepo(self, addon_name, git_url, branch='master'):
		url = ('%s/archive/%s.zip' % (git_url, branch))
		repo_owner = None
		repo_name = None

		m = regex_github_url.match(git_url)
		if m is not None:
			repo_owner = m.group(1).strip()
			repo_name  = m.group(2).strip()

		try:
			with self.httpget(url) as response:
				return self.createDownloadableFromResponse(
					response,
					addon_name=addon_name,
					zip_root=('%s-%s' % (repo_name, branch))
				)

		except urllib.error.HTTPError:
			pass


	def httpget(self, url):
		req = urllib.request.Request(url)
		return urllib.request.urlopen(req)


	def createDownloadableFromResponse(self, response, addon_name=None, zip_root=None):
		url = response.url

		installable = downloadZipFromResponse(
			response,
			name=addon_name,
			source=url,
			zip_root=zip_root
		)

		return DownloadableWrapper(installable)

