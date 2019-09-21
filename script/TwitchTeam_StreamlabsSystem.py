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
    os.path.realpath(__file__)), "./libs/StreamlabsEventReceiver.dll"))
from StreamlabsEventReceiver import StreamlabsEventClient

clr.AddReference("IronPython.SQLite.dll")
clr.AddReference("IronPython.Modules.dll")

#---------------------------------------
#   [Required] Script Information
#---------------------------------------
ScriptName = "Twitch Team Shoutout"
Website = "https://github.com/camalot/chatbot-teamshoutout"
Description = "A script to give a custom shoutout when a member of the listed twitch team hosts or raids your channel."
Creator = "DarthMinos"
Version = "1.0.0-snapshot"

# ---------------------------------------
#	Set Variables
# ---------------------------------------

Repo = "camalot/chatbot-twitchteam"

DonateLink = "https://paypal.me/camalotdesigns"
ReadMeFile = "https://github.com/" + Repo + "/blob/develop/ReadMe.md"


SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")

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
            self.TwitchClientId = ""
            self.StreamlabsToken = ""
            self.HostMessageTemplate = "Fellow $stream_team streamer @$display_name has $action the channel. Make sure you go give them a follow https://twitch.tv/$name"
            self.RaidMessageTemplate = "Fellow $stream_team streamer @$display_name has $action the channel. Make sure you go give them a follow https://twitch.tv/$name"
            self.StreamTeam = ""

            with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
                fileSettings = json.load(f, encoding="utf-8")
                self.__dict__.update(fileSettings)
        except Exception as e:
            Parent.Log(ScriptName, str(e))

    def Reload(self, jsonData):
        fileLoadedSettings = json.loads(jsonData, encoding="utf-8")
        self.__dict__.update(fileLoadedSettings)

#---------------------------------------
#   [Required] Initialize Data / Load Only
#---------------------------------------


def Init():
    # Globals
    global ScriptSettings

    # Load saved settings and validate values
    ScriptSettings = Settings(SettingsFile)

    global EventReceiver
    EventReceiver = StreamlabsEventClient()
    EventReceiver.StreamlabsSocketConnected += EventReceiverConnected
    EventReceiver.StreamlabsSocketDisconnected += EventReceiverDisconnected
    EventReceiver.StreamlabsSocketEvent += EventReceiverEvent

    if ScriptSettings.StreamlabsToken:
        EventReceiver.Connect(ScriptSettings.StreamlabsToken)

    GetTeamList()
    return


def GetTeamList():
    global TeamList
    resp = Parent.GetRequest("https://api.twitch.tv/kraken/teams/" + ScriptSettings.StreamTeam, headers={
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Client-ID': ScriptSettings.TwitchClientId
    }
    )
    obj = json.loads(json.loads(resp)['response'])
    TeamList = obj['users']
    return


def FindUser(user, action):
    global TeamList
    found = next(item for item in TeamList if item["name"] == user)
    if(found):
        return found
    else:
        return None
# ---------------------------------------
# Chatbot Save Settings Function
# ---------------------------------------


def ReloadSettings(jsondata):
    if EventReceiver and EventReceiver.IsConnected:
        EventReceiver.Disconnect()

    # Reload newly saved settings and verify
    global ScriptSettings
    ScriptSettings.Reload(jsondata)

    # Connect if token has been entered and EventReceiver is not connected
    # This can then connect without having to reload the script
    if EventReceiver and not EventReceiver.IsConnected:
        if ScriptSettings.StreamlabsToken:
            EventReceiver.Connect(ScriptSettings.StreamlabsToken)

    # End of ReloadSettings
    return


def EventReceiverConnected(sender, args):
    return


def EventReceiverDisconnected(sender, args):
    return


def EventReceiverEvent(sender, args):
    global ScriptSettings
    global lastParsed
    evntdata = args.Data
    if lastParsed == evntdata.GetHashCode():
        return  # Fixes a strange bug where Chatbot registers to the DLL multiple times
    lastParsed = evntdata.GetHashCode()
    if evntdata and evntdata.For == "twitch_account":
        if evntdata.Type == "host":
            for message in evntdata.Message:
                found = FindUser(message.Name.lower(), evntdata.Type.lower())
                if(found):
                    msg = ReplaceUserProps(
                        ScriptSettings.HostMessageTemplate, found, evntdata.Type.lower())
                    Parent.SendTwitchMessage(msg)
        elif evntdata.Type == "raid":
            for message in evntdata.Message:
                found = FindUser(message.Name.lower(), evntdata.Type.lower())
                if(found):
                    msg = ReplaceUserProps(
                        ScriptSettings.RaidMessageTemplate, found, evntdata.Type.lower())
                    Parent.SendTwitchMessage(msg)
    return


def ReplaceUserProps(template, user, action):
    msg = str.replace(template, "$display_name", user['display_name'])
    msg = str.replace(template, "$stream_team", ScriptSettings.StreamTeam)
    msg = str.replace(msg, "$name", user['name'])
    msg = str.replace(msg, "$action", action + "ed")
    return msg


def Unload():
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

def OpenFollowOnTwitchLink():
    os.startfile("https://twitch.tv/DarthMinos")
    return

def OpenReadMeLink():
    os.startfile(ReadMeFile)
    return
def OpenDonateLink():
    os.startfile(DonateLink)
    return


def OpenSLAPISettingsPage():
    os.system("explorer https://streamlabs.com/dashboard#/settings/api-settings")
    return


def OpenTAPISettingsPage():
    os.system("explorer https://dev.twitch.tv/console/apps/create")
    return

def OpenScriptUpdater():
    currentDir = os.path.realpath(os.path.dirname(__file__))
    chatbotRoot = os.path.realpath(os.path.join(currentDir, "../../../"))
    libsDir = os.path.join(currentDir, "libs/updater")
    try:
        src_files = os.listdir(libsDir)
        tempdir = tempfile.mkdtemp()
        Parent.Log(ScriptName, tempdir)
        for file_name in src_files:
            full_file_name = os.path.join(libsDir, file_name)
            if os.path.isfile(full_file_name):
                Parent.Log(ScriptName, "Copy: " + full_file_name)
                shutil.copy(full_file_name, tempdir)
        updater = os.path.join(tempdir, "ChatbotScriptUpdater.exe")
        updaterConfigFile = os.path.join(tempdir, "update.manifest")
        repoVals = Repo.split('/')
        updaterConfig = {
            "path": os.path.realpath(os.path.join(currentDir,"../")),
            "version": Version,
            "name": ScriptName,
            "requiresRestart": True,
            "kill": [],
            "execute": {
                "before": [],
                "after": []
            },
            "chatbot": os.path.join(chatbotRoot, "Streamlabs Chatbot.exe"),
            "script": os.path.basename(os.path.dirname(os.path.realpath(__file__))),
            "website": Website,
            "repository": {
                "owner": repoVals[0],
                "name": repoVals[1]
            }
        }
        configJson = json.dumps(updaterConfig)
        with open(updaterConfigFile, "w+") as f:
            f.write(configJson)
        os.startfile(updater)
    except OSError as exc: # python >2.5
        raise
