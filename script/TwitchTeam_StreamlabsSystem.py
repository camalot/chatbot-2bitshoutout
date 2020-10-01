#---------------------------------------
#   Import Libraries
#---------------------------------------
import sys
import clr
import json
import codecs
import os
import re
import random
import datetime
import glob
import time
import threading
import shutil
import tempfile
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
ReadMeFile = "https://github.com/" + Repo + "/blob/develop/ReadMe.md"


SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")
UIConfigFile = os.path.join(os.path.dirname(__file__), "UI_Config.json")

EventReceiver = None
ScriptSettings = None
Debug = False
LAST_PARSED = 1
TeamList = None
TeamDisplayName = None
Initialized = False
# ---------------------------------------
#	Script Classes
# ---------------------------------------


class Settings(object):
    """ Class to hold the script settings, matching UI_Config.json. """

    def __init__(self, settingsfile=None):
        """ Load in saved settings file if available else set default values. """
        defaults = self.DefaultSettings(UIConfigFile)
        try:
            SOEPath = os.path.realpath(os.path.join(os.path.dirname(__file__), "../Shoutout"))
            SOEExists = os.path.isdir(SOEPath)
            self.EnableShoutoutHook = SOEExists
            self.__dict__.update(defaults)
            with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
                fileSettings = json.load(f, encoding="utf-8")
                self.__dict__.update(fileSettings)
        except Exception as e:
            self.__dict__.update(defaults)
            Parent.Log(ScriptName, str(e))

    def DefaultSettings(self, settingsfile=None):
        defaults = dict()
        with codecs.open(settingsfile, encoding="utf-8-sig", mode="r") as f:
            ui = json.load(f, encoding="utf-8")
        for key in ui:
            try:
                if "value" in ui[key]:
                    defaults[key] = ui[key]['value']
            except:
                if key != "output_file":
                    Parent.Log(ScriptName, "DefaultSettings(): Could not find key {0} in settings".format(key))
        return defaults

    def Reload(self, jsonData):
        fileLoadedSettings = json.loads(jsonData, encoding="utf-8")
        self.__dict__.update(fileLoadedSettings)

#---------------------------------------
#   [Required] Initialize Data / Load Only
#---------------------------------------


def Init():
    global ScriptSettings
    global EventReceiver
    global Initialized
    global TeamList

    if Initialized:
        return
    ScriptSettings = Settings(SettingsFile)

    EventReceiver = StreamlabsEventClient()
    EventReceiver.StreamlabsSocketConnected += EventReceiverConnected
    EventReceiver.StreamlabsSocketDisconnected += EventReceiverDisconnected
    EventReceiver.StreamlabsSocketEvent += EventReceiverEvent
    Parent.Log(ScriptName, "Loaded")

    if ScriptSettings.StreamlabsToken and not EventReceiver.IsConnected:
        Parent.Log(ScriptName, "Connecting")
        EventReceiver.Connect(ScriptSettings.StreamlabsToken)
    TeamList = list()
    if ScriptSettings.StreamTeam:
        GetTeamList()
    Initialized = True
    return
def ScriptToggled(state):
    if state:
        Init()
    else:
        Unload()
    return

def ReloadSettings(jsondata):
    Unload()
    Init()
    return


def Unload():
    global EventReceiver
    global Initialized
    if EventReceiver is not None:
        EventReceiver.StreamlabsSocketConnected -= EventReceiverConnected
        EventReceiver.StreamlabsSocketDisconnected -= EventReceiverDisconnected
        EventReceiver.StreamlabsSocketEvent -= EventReceiverEvent
        if EventReceiver.IsConnected:
            EventReceiver.Disconnect()
        EventReceiver = None
    Initialized = False    
    return


def Execute(data):
    return


def Tick():
    return

def Parse(parseString, userid, username, targetid, targetname, message):
    # if "$myparameter" in parseString:
    #     return parseString.replace("$myparameter","I am a cat!")
    return parseString

def GetTeamList():
    global TeamList
    global TeamDisplayName
    if ScriptSettings.StreamTeam:
        teams = ScriptSettings.StreamTeam.lower().split(',')
        Parent.Log(ScriptName, "Load Teams: {0}".format(json.dumps(teams)))
        for team in teams:
            url = "https://decapi.me/twitch/team_members/{0}/".format(team.strip())
            resp = Parent.GetRequest(url, headers={})
            obj = json.loads(json.loads(resp)['response'])
            obj_set = set(obj)
            team_set = set(TeamList)
            diff = obj_set - team_set
            TeamDisplayName = ScriptSettings.StreamTeam.lower()
            TeamList = TeamList + list(diff)
            Parent.Log(ScriptName, "TeamList: {0}".format(json.dumps(TeamList)))
        return


def FindUser(user, action):
    global TeamList
    found = next(item for item in TeamList if item.lower() == user.lower())
    if found:
        return found
    else:
        return None

def EventReceiverConnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket connected")
    return


def EventReceiverDisconnected(sender, args):
    Parent.Log(ScriptName, "Streamlabs event websocket disconnected")
    return

def EventReceiverEvent(sender, args):
    global ScriptSettings
    global LAST_PARSED
    evntdata = args.Data
    if LAST_PARSED == evntdata.GetHashCode() or evntdata is None:
        return  # Fixes a strange bug where Chatbot registers to the DLL multiple times
    LAST_PARSED = evntdata.GetHashCode()
    Parent.Log(ScriptName, "type: " + evntdata.Type)
    if evntdata and evntdata.For == "twitch_account":
        if evntdata.Type == "host" and ScriptSettings.EnableHostEvent:
            for message in evntdata.Message:
                Parent.Log(ScriptName, message.Name)
                found = FindUser(message.Name.lower(), evntdata.Type.lower())
                if found:
                    Parent.Log(ScriptName, "Host: Found: " + found) 
                    msg = ReplaceUserProps(ScriptSettings.HostMessageTemplate, found, evntdata.Type.lower())
                    Parent.SendTwitchMessage(msg)
                    Parent.Log(ScriptName, msg) 
                    if ScriptSettings.EnableShoutoutHook:
                        SendUsernameWebsocket(message.Name.lower())
                else:
                    Parent.Log(ScriptName, "Host Not Found")
        elif evntdata.Type == "raid" and ScriptSettings.EnableRaidEvent:
            for message in evntdata.Message:
                found = FindUser(message.Name.lower(), evntdata.Type.lower())
                if found:
                    Parent.Log(ScriptName, "Raid: Found: " + found) 
                    msg = ReplaceUserProps(ScriptSettings.RaidMessageTemplate, found, evntdata.Type.lower())
                    Parent.SendTwitchMessage(msg)
                    Parent.Log(ScriptName, msg) 
                    if ScriptSettings.EnableShoutoutHook:
                        SendUsernameWebsocket(message.Name.lower())
                else:
                    Parent.Log(ScriptName, "Raid Not Found")
    return

def ReplaceUserProps(template, user, action):
    msg = str.replace(template, "$display_name", user)
    msg = str.replace(msg, "$stream_team", 'Stream Team')
    msg = str.replace(msg, "$name", user)
    msg = str.replace(msg, "$action", action + "ed")
    return msg

def SendUsernameWebsocket(username):
    # Broadcast WebSocket Event
    payload = {
        "user": username
    }
    SendWebsocketData("EVENT_SO_COMMAND", payload)
    return
def SendWebsocketData(eventName, payload):
    Parent.Log(ScriptName, "Trigger Event: " + eventName)
    Parent.BroadcastWsEvent(eventName, json.dumps(payload))
    return
def OpenFollowOnTwitchLink():
    os.startfile("https://twitch.tv/DarthMinos")
    return

def OpenShoutoutOverlayLink():
    os.startfile("https://github.com/camalot/chatbot-shoutout")
    return

def OpenReadMeLink():
    os.startfile(ReadMeFile)
    return

def OpenPaypalDonateLink():
    os.startfile("https://paypal.me/camalotdesigns/10")
    return
def OpenGithubDonateLink():
    os.startfile("https://github.com/sponsors/camalot")
    return
def OpenTwitchDonateLink():
    os.startfile("http://twitch.tv/darthminos/subscribe")
    return
def OpenSLAPISettingsLink():
    os.startfile("https://streamlabs.com/dashboard#/settings/api-settings")
    return

def OpenTwitchClientIdLink():
    os.startfile("https://dev.twitch.tv/console/apps/create")
    return
    
def OpenDiscordLink():
    os.startfile("https://discord.com/invite/vzdpjYk")
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
        updater = os.path.join(tempdir, "ApplicationUpdater.exe")
        updaterConfigFile = os.path.join(tempdir, "update.manifest")
        repoVals = Repo.split('/')
        updaterConfig = {
            "path": os.path.realpath(os.path.join(currentDir,"../")),
            "version": Version,
            "name": ScriptName,
            "requiresRestart": True,
            "kill": [],
            "execute": {
                "before": [{
                    "command": "cmd",
                    "arguments": [ "/c", "del /q /f /s *" ],
                    "workingDirectory": "${PATH}\\${FOLDERNAME}\\Libs\\updater\\",
                    "ignoreExitCode": True,
                    "validExitCodes": [ 0 ]
                }],
                "after": []
            },
            "application": os.path.join(chatbotRoot, "Streamlabs Chatbot.exe"),
            "folderName": os.path.basename(os.path.dirname(os.path.realpath(__file__))),
            "processName": "Streamlabs Chatbot",
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
