import QtMultimedia 5.9
import QtQuick.Layouts 1.4
import QtQuick 2.9
import QtQuick.Controls 2.2
import org.kde.kirigami 2.4 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Mycroft.Delegate {
    id: root
    skillBackgroundSource: sessionData.audioThumb

    Mycroft.AudioPlayer {
        id: exampleAudioPlayer
        anchors.fill: parent
        source: sessionData.audioSource
        thumbnail: sessionData.audioThumb
        title: sessionData.audioTitle
        status: sessionData.status
        nextAction: "colla69.plex-audio-player.next"
        previousAction: "colla69.plex-audio-player.prev"

        onCurrentStateChanged: {
            console.log("playing: \n" + sessionData.audioSource)
            if(currentState == MediaPlayer.EndOfMedia) {

                triggerGuiEvent("colla69.plex-audio-player.next", {})
            }
        }

    }
}

