import os
import random
import sys
import time
from collections import defaultdict
import re
from mycroft.skills.core import intent_file_handler
from mycroft.util.log import LOG
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from json import load, dump
import vlc
import xml.etree.ElementTree as ET
import requests

__author__ = 'colla69'


def refresh_library(path):
    pass


class PlexMusicSkill(CommonPlaySkill):

    def CPS_match_query_phrase(self, phrase):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            phrase = re.sub(self.translate_regex('on_plex'), '', phrase)
            title = ""
            artist = ""
            album = ""
            t_prob = 0
            a_prob = 0
            al_prob = 0
            if phrase.startswith("artist"):
                artist, a_prob = self.artist_search(phrase[7:])
            elif phrase.startswith("album"):
                album, al_prob = self.album_search(phrase[6:])
            else:
                title, t_prob = self.title_search(phrase)
                artist, a_prob = self.artist_search(phrase)
                album, al_prob = self.album_search(phrase)
            print(""" Plex Music skill
    Title   %s  %f
    Artist  %s  %d
    Album   %s  %d        
            """ % (title, t_prob, artist, a_prob, album, al_prob))
            if t_prob > al_prob and t_prob > a_prob:
                data = {
                    "title": title,
                    "file": self.titles[title]
                }
                return phrase, CPSMatchLevel.TITLE, data
            elif a_prob >= al_prob:
                data = {
                    "title": artist,
                    "file": self.artists[artist]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            elif al_prob > a_prob:
                data = {
                    "title": album,
                    "file": self.albums[album]
                }
                return phrase, CPSMatchLevel.MULTI_KEY, data
            else:
                return None

    def CPS_start(self, phrase, data):
        if data == None:
            return None
        if self.get_running():
            self.player.get_media_player().audio_set_volume(80)
            self.player.stop()                        
        LOG.info(data)
        title = data["title"]
        link = data["file"]
        random.shuffle(link)
        LOG.info(data)
        try:
            if len(link) >= 1:
                self.player = self.vlcI.media_list_player_new()
                m = self.vlcI.media_list_new(link)
                self.player.set_media_list(m)
                self.player.play()
            else:
                self.player = self.vlcI.media_player_new()
                m = self.vlcI.media_new(link)
                self.player.set_media(m)
                self.player.play()
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
        uri = self.settings.get("musicsource", "")
        token = self.settings.get("plextoken", "")
        self.lib_name = self.settings.get("plexlib", "")
        self.ducking = self.settings.get("ducking", "True")
        self.regexes = {}
        self.refreshing_lib = False
        self.p_uri = uri+":32400"
        self.p_token = "?X-Plex-Token="+token
        self.data_path = os.path.expanduser("~/.config/plexSkill/data.json")
        self.artists = defaultdict(list)
        self.albums = defaultdict(list)
        self.titles = defaultdict(list)
        self.vlcI = vlc.Instance()
        self.player = self.vlcI.media_list_player_new()
        self.player.get_media_player().audio_set_volume(100)

    def initialize(self):
        if not os.path.isfile(self.data_path):
            self.speak_dialog("library.unknown")
        self.load_data()
        self.add_event('recognizer_loop:record_begin', self.handle_listener_started)
        self.add_event('recognizer_loop:record_end', self.handle_listener_stopped)
        self.add_event('recognizer_loop:audio_output_start', self.handle_audio_start)
        self.add_event('recognizer_loop:audio_output_end', self.handle_audio_stop)

    def get_running(self):
        return self.player.is_playing()

    def load_data(self):
        LOG.info("loading "+self.data_path)
        if not os.path.isfile(self.data_path):
            LOG.info("making new JsonData ")
            self.down_plex_lib()
            self.speak_dialog("done")
        data = self.json_load(self.data_path)
        for artist in data:
            for album in data[artist]:
                for song in data[artist][album]:
                    title = song[0]
                    file = song[1]
                    self.albums[album].append(file)
                    self.artists[artist].append(file)
                    self.titles[title].append(file)

    # thanks to forslund
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    ###################################
    # Utils

    def json_save(self, data, fname):
        with open(fname, 'w') as fp:
            dump(data, fp)

    def json_load(self, fname):
        with open(fname, 'r') as fp:
            return load(fp)

    def get_tokenized_uri(self, uri):
        return self.p_uri + uri + self.p_token

    def title_search(self, phrase):
        probabilities = process.extractOne(phrase, self.titles.keys(), scorer=fuzz.ratio)
        artist = probabilities[0]
        confidence = probabilities[1]
        return artist, confidence

    def artist_search(self, phrase):
        probabilities = process.extractOne(phrase, self.artists.keys(), scorer=fuzz.ratio)
        artist = probabilities[0]
        confidence = probabilities[1]
        return artist, confidence

    def album_search(self, phrase):
        probabilities = process.extractOne(phrase, self.albums.keys(), scorer=fuzz.ratio)
        album = probabilities[0]
        confidence = probabilities[1]
        return album, confidence

    def down_plex_lib(self):
        self.refreshing_lib = True
        try:
            xml = requests.get(self.get_tokenized_uri("/library/sections")).text
            root = ET.fromstring(xml)
            LOG.info(self.get_tokenized_uri("/library/sections"))
            for child in root:
                print()
                if self.lib_name == child.attrib["title"].lower():
                    artisturi = self.get_tokenized_uri("/library/sections/" + child.attrib["key"] + "/all")
            xml = requests.get(artisturi).text
            root = ET.fromstring(xml)
            artists = defaultdict(list)
            albums = defaultdict(list)
            titles = defaultdict(list)
            count = 0
            songs = {}
            for artist in root:
                songs[artist.get("title")] = {}
                artist_uri = self.get_tokenized_uri(artist.get("key"))
                plexalbums = ET.fromstring(requests.get(artist_uri).text)
                for album in plexalbums:
                    songs[artist.get("title")][album.get("title")] = []
                    album_uri = self.get_tokenized_uri(album.get("key"))
                    plexsongs = ET.fromstring(requests.get(album_uri).text)
                    for songmeta in plexsongs:
                        song_uri = self.get_tokenized_uri(songmeta.get("key"))
                        try:
                            s = requests.get(song_uri).text
                            if s == "":
                                continue
                        except:
                            continue
                        song = ET.fromstring(s)
                        for p in song.iter("Part"):
                            title = songmeta.get("title")
                            file = self.get_tokenized_uri(p.get("key"))
                            songs[artist.get("title")][album.get("title")].append([title, file])
                            # print(songs)
                            # albums[album.get("title")].append(file)
                            # artists[artist.get("title")].append(file)
                            # titles[song.get("title")].append(file)
                            print("""%d 
            %s -- %s 
            %s

                            """ % (count, artist.get("title"), album.get("title"), title))
                            count += 1
            self.json_save(songs, self.data_path)
            LOG.info("done loading library")
        finally:
            self.refreshing_lib = False

    ######################################################################
    # audio ducking

    def lower_volume_onethird(self):
        if self.get_running():
            volume = self.player.get_media_player().audio_get_volume()
            volume = (volume // 3) * 2
            self.player.get_media_player().audio_set_volume(volume)

    def raise_volume_onethird(self):
        if self.get_running():
            volume = self.player.get_media_player().audio_get_volume()
            volume = (volume // 2) * 3
            self.player.get_media_player().audio_set_volume(volume)

    def handle_listener_started(self, message):
        if self.ducking:
            self.lower_volume_onethird()

    def handle_listener_stopped(self, message):
        if self.ducking:
            self.raise_volume_onethird()

    def handle_audio_start(self, event):
        if self.ducking:
            self.lower_volume_onethird()

    def handle_audio_stop(self, event):
        if self.ducking:
            self.raise_volume_onethird()

    ##################################################################
    # intents

    @intent_file_handler('play.music.intent')
    def handle_play_music_intent(self, message):
        pass

    @intent_file_handler('resume.music.intent')
    def handle_resume_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.player.play()

    @intent_file_handler('pause.music.intent')
    def handle_pause_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.player.pause()

    @intent_file_handler('next.music.intent')
    def handle_next_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.player.next()

    @intent_file_handler('prev.music.intent')
    def handle_prev_music_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("refresh.library")
            return None
        else:
            self.player.previous()

    @intent_file_handler('reload.library.intent')
    def handle_reload_library_intent(self, message):
        if self.refreshing_lib:
            self.speak_dialog("already.refresh.library")
            return None
        else: 
            self.speak_dialog("refresh.library")
            os.remove(self.data_path)
            self.load_data()

    def converse(self, utterances, lang="en-us"):
        return False

    def stop(self):
        self.player.stop()
        self.vlcI.release()


def create_skill():
    return PlexMusicSkill()

