#---------------------------------------
#   Import Libraries
#---------------------------------------
import sys
import clr
import json
import codecs
import os
#import weakref
# point at lib folder for classes / references
sys.path.append(os.path.join(os.path.dirname(__file__), "..\Libs"))
clr.AddReferenceToFileAndPath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "StreamlabsEventReceiver.dll"))
from StreamlabsEventReceiver import StreamlabsEventClient

clr.AddReference("IronPython.SQLite.dll")
clr.AddReference("IronPython.Modules.dll")

#---------------------------------------
#   [Required] Script Information
#---------------------------------------
ScriptName = "2Bit Shoutout"
Website = "https://github.com/camalot/chatbot-2bitshoutout"
Description = ""
Creator = "DarthMinos"
Version = "1.0.0"

# ---------------------------------------
#	Set Variables
# ---------------------------------------


SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")
ReadMeFile = os.path.join(os.path.dirname(__file__), "README.md")
EventReceiver = None
lastParsed = None
ScriptSettings = None
Debug = False
lastParsed = 1
TeamList = None
# ---------------------------------------
#	Script Classes
# ---------------------------------------


class Settings(object):
    """ Class to hold the script settings, matching UI_Config.json. """

    def __init__(self, settingsfile=None):
        """ Load in saved settings file if available else set default values. """
        try:
            with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
                self.__dict__ = json.load(f, encoding="utf-8")
        except:
            self.twitch_clientid = ""
            self.streamlabs_token = ""
            self.MessageTemplate = "Fellow 2BIT Community streamer @$display_name has hosted the channel. Make sure you go give them a follow https://twitch.tv/$name"
            self.stream_team = "2bitcommunity"

    def Reload(self, jsonData):
        """ Reload settings from the user interface by given json data. """
        self.__dict__ = json.loads(jsonData, encoding="utf-8")

#---------------------------------------
#   [Required] Initialize Data / Load Only
#---------------------------------------


def Init():
    """ Initialize script or startup or reload. """
    Parent.Log(ScriptName, SettingsFile)

    # Globals
    global ScriptSettings

    # Load saved settings and validate values
    ScriptSettings = Settings(SettingsFile)

    global EventReceiver
    EventReceiver = StreamlabsEventClient()
    EventReceiver.StreamlabsSocketConnected += EventReceiverConnected
    EventReceiver.StreamlabsSocketDisconnected += EventReceiverDisconnected
    EventReceiver.StreamlabsSocketEvent += EventReceiverEvent
    Parent.Log(ScriptName, "Loaded")

    if ScriptSettings.streamlabs_token:
        Parent.Log(ScriptName, "Connecting")
        EventReceiver.Connect(ScriptSettings.streamlabs_token)

    GetTeamList()
    return


def GetTeamList():
    global TeamList
    resp = Parent.GetRequest("https://api.twitch.tv/kraken/teams/" + ScriptSettings.stream_team, headers={
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Client-ID': ScriptSettings.twitch_clientid
    }
    )
    obj = json.loads(json.loads(resp)['response'])
    TeamList = obj['users']
    return


def FindUser(user):
    global TeamList
    found = next(item for item in TeamList if item["name"] == user)
    if(found):
        Parent.SendTwitchMessage(str.replace(str.replace(
            ScriptSettings.MessageTemplate, "$display_name", found['display_name']), "$name", found['name']))
# ---------------------------------------
# Chatbot Save Settings Function
# ---------------------------------------


def ReloadSettings(jsondata):
    Parent.Log(ScriptName, "Reload")

    if EventReceiver and EventReceiver.IsConnected:
        EventReceiver.Disconnect()

    # Reload newly saved settings and verify
    global ScriptSettings
    ScriptSettings.Reload(jsondata)

    # Connect if token has been entered and EventReceiver is not connected
    # This can then connect without having to reload the script
    if EventReceiver and not EventReceiver.IsConnected:
        Parent.Log(ScriptName, "NOT CONNECTED")
        if ScriptSettings.streamlabs_token:
            EventReceiver.Connect(ScriptSettings.streamlabs_token)

    # End of ReloadSettings
    return


def EventReceiverConnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket connected")
    return


def EventReceiverDisconnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket disconnected")
    return


def EventReceiverEvent(sender, args):
    evntdata = args.Data
    global ScriptSettings
    global lastParsed
    if lastParsed == evntdata.GetHashCode():
        return  # Fixes a strange bug where Chatbot registers to the DLL multiple times
    lastParsed = evntdata.GetHashCode()
    if evntdata and evntdata.For == "twitch_account":
        if evntdata.Type == "host":
            for message in evntdata.Message:
                FindUser(message.Name.lower())
        elif evntdata.Type == "raid":
                FindUser(message.Name.lower())
    return


def Unload():
    Parent.Log(ScriptName, "Unload")

    # Disconnect EventReceiver cleanly
    global EventReceiver
    if EventReceiver and EventReceiver.IsConnected:
        EventReceiver.Disconnect()
    EventReceiver = None

    # End of Unload
    return


def Execute(data):
    return


def Tick():
    return


def OpenSLAPISettingsPage():
    os.system("explorer https://streamlabs.com/dashboard#/settings/api-settings")
    return


def OpenTAPISettingsPage():
    os.system("explorer https://dev.twitch.tv/console/apps/create")
    return


def OpenReadMe():
    """ Open the script readme file in users default .txt application. """
    os.startfile(ReadMeFile)
    return
