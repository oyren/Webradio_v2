import QtQuick 1.0


Rectangle {
    id: mainScreen
    property int currentIndex: 0
    width: 270
    height: 112
    color: "transparent"

    Image {
        id: image1
        x: 0
        y: 0
        width: 270
        height: 111
        source: "bomb.png"

        Text {
            id: counter
            objectName: "counter_text"
            x: 52
            y: 15
            width: 116
            height: 58
            color: "#e40000"
            text: qsTr("00:00:00")
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            anchors.verticalCenterOffset: -19
            anchors.horizontalCenterOffset: 3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: 25
        }
    }



}

