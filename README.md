## Localmusicplayer

### Description

This Mycroft skill can play music from your plex media server with speech commands.

### Requirements
  you will need access to a plex media server and a working installation of vlc
  
  ##### get vlc
  Debian/Ubuntu `sudo apt install vlc`  
  CentOs        `sudo yum install vlc`  
  Arch/Manjaro  `sudo pacman -S vlc`   
    
### Install
  `msm install https://github.com/colla69/plexmusic-skill.git`
  
### Examples
 - "Hey mycroft, play eminem!"
 - "Hey mycroft, play album meteora"
 
### Functions
  - Play [title|artist|album] <br>
    Play artist|album *name*    
  - Pause music
  - Resume music
  - Next|Skip
  - Reload library | Refresh library 

### Usage
  First go to https://account.mycroft.ai/skills and find the Plex Music Skill.<br>
  Please fill in the 3 fields:
   - plex uri (address of your PlexMediaServer, it has to be reachable on port 32400)
   - plex token (for info visit https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
   - Library name in plex  (the name of the library to play the music from)
  
  The first intallation will need to download all your library metadata and will save it in a JSON file. 
  (~/.config/plexSkill/data.json) <br> 
  The process will take a long time, don't panic, you can watch it load if you have debug=True in your config. 

### Credits
colla69


