
from wowupdate.updater.CurseUpdater import CurseUpdater
from wowupdate.updater.GithubUpdater import GithubUpdater
from wowupdate.updater.TSMUpdater import TSMUpdater


class Config:
	def __init__(self):
		self.addons_dir = None
		self.config = {}
		self.updaters = [
			CurseUpdater(self),
			GithubUpdater(self),
			TSMUpdater(self)
		]


	def getConfig(self, key):
		if key in self.config:
			return self.config[key]

		return None


