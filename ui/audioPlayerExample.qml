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
        nextAction: "colla69.plex-audio-player.next"
        previousAction: "colla69.plex-audio-player.prev"
    }

    Component.onCompleted: {
        exampleAudioPlayer.status = "play"
    }

    RoundButton {
        id: backButton
        anchors.top: parent.top
        anchors.left: parent.right
        implicitWidth: Kirigami.Units.iconSizes.large
        implicitHeight: implicitWidth
        icon.name: "go-previous-symbolic"
        onClicked: {
            triggerGuiEvent("PlexMusicSkill.next", {})
            exampleAudioPlayer.pause
        }
    }
}

