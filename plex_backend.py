from collections import defaultdict
from json import load, dump
from plexapi.server import PlexServer

class PlexBackend():

    def __init__(self, plexurl, token, libname, data_path):
        self.token = token
        self.plexurl = plexurl
        self.lib_name = libname
        self.data_path = data_path
        self.plex = PlexServer(self.plexurl, self.token)
        self.music = self.plex.library.section(self.lib_name)
        self.playlists = []
                       
    def down_plex_lib(self):
        songs = {}
        try:
            self.playlists = self.plex.playlists()
            songs["playlist"] = {}
            for p in self.playlists:
                p_name = p.title
                songs["playlist"][p_name] = []
                for track in p.items():
                    title = track.title
                    album = track.album().title
                    artist = track.artist().title
                    file_key = self.get_file(track)
                    file = self.get_tokenized_uri( file_key )
                    songs["playlist"][p_name].append([artist, album, title, file])
            root = self.music.all()
            artists = defaultdict(list)
            albums = defaultdict(list)
            titles = defaultdict(list)
            count = 0
            for artist in root:
                artist_title = artist.title
                songs[artist_title] = {}
                for album in artist.albums():
                    album_title = album.title
                    songs[artist_title][album_title] = []
                    for track in album.tracks():
                        title = track.title
                        file_key = self.get_file(track)
                        file = self.get_tokenized_uri( file_key )
                        try:
                            print("""%d 
            %s -- %s 
            %s
            %s

                            """ % (count, artist_title, album_title, title,file_key))
                            songs[artist_title][album_title].append([title, file])
                            count += 1
                        except Exception as ex:
                            print(ex)
            self.json_save(songs, self.data_path)
            print("done loading library")
        except Exception as e:
            print(e)
            return None

    def json_save(self, data, fname):
        with open(fname, 'w') as fp:
            dump(data, fp)

    def json_load(self, fname):
        with open(fname, 'r') as fp:
            return load(fp)
        
    def get_tokenized_uri(self, uri):
        return self.plexurl+uri+"?X-Plex-Token="+self.token

    def get_file(self,track):
        for media in track.media:
            for p in media.parts:
                return p.key

    def add_to_playlist(self, playlist_name, artist, album, title ):
        print("""\nadding to playlist:
        {}   by   {}  
        Album: {}        
                    """.format(title, artist, album))
        for p in self.playlists:
            p_name = p.title
        root = self.music.all()
        """for artist in root:            
            artist_title = artist.title
            for album in artist.albums():
                album_title = album.title
                for track in album.tracks():
                    title = track.title
                print(".")"""
        print("done")