# MIT LICENSE
# Mycroft Skill: Application Launcher, opens/closes Linux desktop applications
# Copyright © 2019 Philip Mayer philip.mayer@shadowsith.de

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import os
import random
import re
import sys
import time
from collections import defaultdict
from json import load, dump

from adapt.intent import IntentBuilder
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from mycroft.audio.services.vlc import VlcService
from mycroft.skills import resting_screen_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.core import intent_handler
from mycroft.util.log import LOG
from .plex_backend import PlexBackend

__author__ = 'colla69'


class PlexMusicSkill(CommonPlaySkill):

    def CPS_match_query_phrase(self, phrase):
        # self.gui.clear()
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            phrase = re.sub(self.translate_regex('on_plex'), '', phrase)
            title = ""
            artist = ""
            album = ""
            playlist = ""
            t_prob = 0
            a_prob = 0
            al_prob = 0
            p_prob = 0
            if "random" in phrase and "music" in phrase:
                data = {
                    "title": "random",
                    "file": self.titles
                }
                return phrase, CPSMatchLevel.TITLE, data
            elif phrase.startswith("artist"):
                artist, a_prob = self.artist_search(phrase[7:])
            elif phrase.startswith("album"):
                album, al_prob = self.album_search(phrase[6:])
            elif phrase.startswith("playlist"):
                playlist, p_prob = self.playlist_search(phrase[9:])
            else:
                title, t_prob = self.title_search(phrase)
                artist, a_prob = self.artist_search(phrase)
                album, al_prob = self.album_search(phrase)
                playlist, p_prob = self.playlist_search(phrase)
                by_title, by_prob = self.by_search(phrase)
            print(""" Plex Music skill
	Title      %s  %f
	Artist     %s  %d
	Album      %s  %d        
	Playlist   %s  %d        
	by Search  %s  %d        
			""" % (title, t_prob, artist, a_prob, album, al_prob, playlist, p_prob, by_title, by_prob))
            if t_prob > al_prob and t_prob > a_prob:
                data = {
                    "title": title,
                    "file": self.titles[title]
                }
                return phrase, CPSMatchLevel.TITLE, data
            elif a_prob >= al_prob and a_prob != 0:
                data = {
                    "title": artist,
                    "file": self.artists[artist]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            elif al_prob >= a_prob and al_prob != 0:
                data = {
                    "title": album,
                    "file": self.albums[album]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            elif p_prob > al_prob:
                data = {
                    "title": playlist,
                    "file": self.playlists[playlist]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            elif by_prob > p_prob:
                data = {
                    "title": by_title,
                    "file": self.tracksByArtist[by_title]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            else:
                return None

    def CPS_start(self, phrase, data):
        if data is None:
            return None
        self.vlc_player.stop()
        self.vlc_player.clear_list()
        title = data["title"]
        link = data["file"]
        if title == "random":
            link = list(link.values())
        random.shuffle(link)
        try:
            self.vlc_player.add_list(link)
            self.vlc_player.play()
            # self.gui["audioSource"] = link
            self.refresh_gui()
        except Exception as e:
            LOG.info(type(e))
            LOG.info("Unexpected error:", sys.exc_info()[0])
            raise
        finally:
            time.sleep(2)
            if not self.get_running():
                self.speak_dialog("playback.problem")
                self.speak_dialog("excuses")

    def __init__(self):
        super().__init__(name="TemplateSkill")
        self.uri = ""
        self.token = ""
        self.lib_name = ""
        self.ducking = "True"
        self.regexes = {}
        self.refreshing_lib = False
        self.p_uri = self.uri
        self.p_token = "?X-Plex-Token=" + self.token
        self.data_path = os.path.expanduser("~/.config/plexSkill/")
        if not os.path.exists(self.data_path):
            os.mkdir(self.data_path)
        self.data_path += "data.json"
        self.plex = None
        self.artists = defaultdict(list)
        self.albums = defaultdict(list)
        self.titles = defaultdict(list)
        self.playlists = defaultdict(list)
        self.tracksByArtist = defaultdict(list)
        self.tracks = {}
        self.vlc_player = None

    def initialize(self):
        self.uri = self.settings.get("musicsource", "")
        self.token = self.settings.get("plextoken", "")
        self.lib_name = self.settings.get("plexlib", "")
        self.ducking = self.settings.get("ducking", "True")
        self.p_uri = self.uri
        if self.load_plex_backend():
            if not os.path.exists(self.data_path):
                self.speak_dialog("library.unknown")
            self.load_data()
        self.vlc_player = VlcService(config={'duck': self.ducking})
        self.vlc_player.normal_volume = 85
        self.vlc_player.low_volume = 20
        self.gui.register_handler('colla69.plex-audio-player.next', self.handle_next_music_intent)
        self.gui.register_handler('colla69.plex-audio-player.prev', self.handle_prev_music_intent)

    def get_running(self):
        return self.vlc_player.player.is_playing()

    def load_data(self):
        LOG.info("loading " + self.data_path)
        try:
            if not os.path.isfile(self.data_path):
                LOG.info("making new JsonData")
                if self.load_plex_backend():
                    self.plex.down_plex_lib()
                    self.speak_dialog("done")
            data = self.json_load(self.data_path)
            for artist in data:
                if artist == "playlist":
                    for playlist in data[artist]:
                        for song in data[artist][playlist]:
                            p_artist = song[0]
                            album = song[1]
                            title = song[2]
                            file = song[3]
                            key = song[4]
                            self.playlists[playlist].append(file)
                            self.tracks[file] = (p_artist, album, title, key)
                for album in data[artist]:
                    for song in data[artist][album]:
                        title = song[0]
                        file = song[1]  # link
                        key = song[2]
                        self.albums[album].append(file)
                        self.artists[artist].append(file)
                        self.titles[title].append(file)
                        self.tracks[file] = (artist, album, title, key)
                        # todo make separator translatable
                        bySearchValue = title + " by " + artist
                        self.tracksByArtist[bySearchValue].append(file)
        finally:
            self.refreshing_lib = False

    def load_plex_backend(self):
        if self.plex is None:
            LOG.info("""\n\n\t connecting to:
			{} {} 
			{} 
			""".format(self.p_uri, self.lib_name, self.token))
            if self.token and self.p_uri and self.lib_name:
                self.plex = PlexBackend(self.p_uri, self.token, self.lib_name, self.data_path)
                return True
            else:
                self.speak_dialog("config.missing")
                return False
        else:
            return True

    def title_search(self, phrase):
        return self.search(phrase, self.titles)

    def artist_search(self, phrase):
        return self.search(phrase, self.artists)

    def album_search(self, phrase):
        return self.search(phrase, self.albums)

    def playlist_search(self, phrase):
        return self.search(phrase, self.playlists)

    def by_search(self, phrase):
        return self.search(phrase, self.tracksByArtist)

    def search(self, phrase, searching_list):
        if searching_list:
            probabilities = process.extractOne(phrase, searching_list.keys(), scorer=fuzz.ratio)
            result = probabilities[0]
            confidence = probabilities[1]
            return result, confidence
        else:
            return "", 0

    def get_active_track_info(self):
        meta = self.vlc_player.track_info()
        artist, album, title = meta["artists"], meta["album"], meta["name"]
        if title.startswith("file"):
            media = self.vlc_player.player.get_media()
            link = media.get_mrl()
            artist, album, title = self.tracks[link]
            if isinstance(artist, list):
                artist = artist[0]
        return album, artist, title

    ######################################################################
    # utils

    def json_save(self, data, fname):
        with open(fname, 'w') as fp:
            dump(data, fp)

    def json_load(self, fname):
        with open(fname, 'r') as fp:
            return load(fp)

    def get_tokenized_uri(self, uri):
        return self.plex.get_tokenized_uri(uri)

    # thanks to forslund
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    def get_music_info(self):
        if self.get_running():
            self.refresh_gui()
            meta = self.vlc_player.track_info()
            title = meta["name"]
            if title.startswith("file"):
                media = self.vlc_player.player.get_media()
                link = media.get_mrl()
                artist, album, title, key = self.tracks[link]
                if isinstance(artist, list):
                    artist = artist[0]
            try:
                return artist, album, title, link, key
            except:
                return "", album, title, link, key
        else:
            return "", "", "", "", ""

    def refresh_gui(self):
        time.sleep(0.5)
        artist, album, title, link, key = self.get_music_info()
        # self.gui["audioSource"] = link
        self.gui.clear()
        self.gui["audioThumb"] = self.get_thumbnail(key)
        self.gui["audioTitle"] = "{}\n{}".format(artist, title)
        self.gui.show_page("audioPlayerExample.qml", override_idle=True)

    def get_thumbnail(self, key):
        xml = requests.get(self.get_tokenized_uri(key)).text
        xml_obj = ET.fromstring(xml)
        thumb = ""
        for x in xml_obj:
            thumb = x.get("grandparentThumb")
            if thumb is None:
                thumb = x.get("parentThumb")
            if thumb is None:
                thumb = ""
        return self.get_tokenized_uri(thumb)

    ##################################################################
    # intents

    @intent_handler(IntentBuilder("ResumeMusicIntent").require("resume.music"))
    def handle_resume_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.vlc_player.play()
            self.refresh_gui()

    @intent_handler(IntentBuilder("PauseMusicIntent").require("pause.music"))
    def handle_pause_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.vlc_player.pause()
            self.refresh_gui()

    @intent_handler(IntentBuilder("NextMusicIntent").require("next.music"))
    def handle_next_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.vlc_player.next()
            self.refresh_gui()

    @intent_handler(IntentBuilder("PrevMusicIntent").require("prev.music"))
    def handle_prev_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.vlc_player.previous()
            self.refresh_gui()

    @intent_handler(IntentBuilder("InfoMusicIntent").require("information"))
    def handle_music_information_intent(self, message):
        if self.get_running():
            artist, album, title, link = self.get_music_info()
            LOG.info("""\nPlex skill is playing:
{}   by   {}  
Album: {}        
			""".format(title, artist, album))
            self.refresh_gui()
            self.speak_dialog('information', data={'title': title, "artist": artist})

    @intent_handler(IntentBuilder("ReloadLibraryIntent").require("reload.library"))
    def handle_reload_library_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("already.refresh.library")
            return None
        else:
            self.refreshing_lib = True
            self.speak_dialog("refresh.library")
            try:
                os.remove(self.data_path)
            except FileNotFoundError:
                pass
            self.load_data()

    def converse(self, utterances, lang="en-us"):
        return False

    def stop(self):
        self.vlc_player.stop()
        self.gui.clear()


def create_skill():
    return PlexMusicSkill()
