# -*- coding: utf-8 -*-

"""
The catalog databases, shared by the catalog modules
"""

from resources.lib.libraries import control
from resources.lib.models import episodes, shows, showcast

# Load DB
episodeDB = episodes.Episode(control.episodesFile)
showDB = shows.Show(control.showsFile)
castDB = showcast.ShowCast(control.celebritiesFile)
