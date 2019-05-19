import os
import time
from collections import defaultdict

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_file_handler, intent_handler
from mycroft.util.log import LOG
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import eyed3
from json import load, dump


__author__ = 'colla69'


eyed3.log.setLevel("ERROR")


def refresh_library(path):
    pass


class PlexMusicSkill(CommonPlaySkill):
    def CPS_match_query_phrase(self, phrase):
        LOG.info("local music")
        title, t_prob = self.title_search(phrase)
        artist, a_prob = self.artist_search(phrase)
        album, al_prob = self.album_search(phrase)
        print("""
%s %d
%s %d
%s %d        
        """ % (title, t_prob, artist, a_prob, album, al_prob))
        return phrase, CPSMatchLevel.TITLE

    def CPS_start(self, phrase, data):
        # search_player(phrase)
        pass

    def __init__(self):
        super().__init__(name="TemplateSkill")
        self.music_source = self.settings.get("musicsource", "")
        self.artists = defaultdict(list)
        self.albums = defaultdict(list)
        self.titles = defaultdict(list)


    def initialize(self):
        self.load_data()

    def load_data(self):
        datapath = os.path.realpath("../../../" + self.music_source.strip() + "data.json")
        LOG.info("loading "+datapath)
        if os.path.isfile(datapath):
            data = self.json_load(datapath)
        else:
            """ dialog uh I don't seem to know your library yet """
            """ dialog let me load that for you, """
            """ dialog this could take some time """
            LOG.info("making new JsonData ")
            #f_count, data, errors = self.get_data_from_dir()
            #print("loaded " + str(f_count) + " files , with " + str(errors) + " errors")
            #self.json_save(data, self.rootDir+"data.json")
            """ dialog we are ready to go """

        for artist in data:
            for album in data[artist]:
                for song in data[artist][album]:
                    title = song[0]
                    file = song[1]
                    self.albums[album].append(file)
                    self.artists[artist].append(file)
                    self.titles[title].append(file)

    def json_save(self, data, fname):
        with open(fname, 'w') as fp:
            dump(data, fp)

    def json_load(self, fname):
        with open(fname, 'r') as fp:
            return load(fp)

    def title_search(self, phrase):
        probabilities = process.extractOne(phrase, self.titles.keys(), scorer=fuzz.ratio)
        title = probabilities[0]
        confidence = probabilities[1]
        if confidence > 0:
            return title, confidence
        else:
            return "Null", 0

    def artist_search(self, phrase):
        probabilities = process.extractOne(phrase, self.artists.keys(), scorer=fuzz.ratio)
        artist = probabilities[0]
        confidence = probabilities[1]
        if confidence > 0:
            return artist, confidence
        else:
            return "Null", 0

    def album_search(self, phrase):
        probabilities = process.extractOne(phrase, self.albums.keys(), scorer=fuzz.ratio)
        album = probabilities[0]
        confidence = probabilities[1]
        if confidence > 0:
            return album, confidence
        else:
            return "Null", 0

    @intent_file_handler('play.music.intent')
    def handle_play_music_ntent(self, message):
        self.activate_player()


    @intent_file_handler('pause.music.intent')
    def handle_pause_music_intent(self, message):
        self.activate_player()


    @intent_file_handler('reload.library.intent')
    def handle_reload_library_intent(self, message):
        refresh_library(self.music_source)
        self.speak_dialog("refresh.library")

    def converse(self, utterances, lang="en-us"):
        return False

    def stop(self):
        pass
        # if getrunning():
        #  self.stop_player()


def create_skill():
    return PlexMusicSkill()

