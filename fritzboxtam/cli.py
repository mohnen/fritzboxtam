import requests
from requests.auth import HTTPDigestAuth
from typing import Optional

from xml.dom.minidom import parseString

import xmltodict

import typer
from typing_extensions import Annotated
from rich import print

main = typer.Typer(no_args_is_help=True)

boxIP = "fritz.box"

def soapXML(action, uri, args=""):
    soapAction = f'{uri}#{action}'
    soapData = f"<?xml version='1.0' encoding='utf-8'?><s:Envelope s:encodingStyle='http://schemas.xmlsoap.org/soap/encoding/' xmlns:s='http://schemas.xmlsoap.org/soap/envelope/'><s:Body><u:{action} xmlns:u='{uri}'>{args}</u:{action}></s:Body></s:Envelope>"
    return (soapAction, soapData)

def getTAM(fritzbox_ip, digest):
    location = "/upnp/control/x_tam"
    (action, data) = soapXML('GetMessageList', 'urn:dslforum-org:service:X_AVM-DE_TAM:1', '<NewIndex>0</NewIndex>')
    url = f'http://{fritzbox_ip}:49000{location}'
    res = requests.post(url, data=data, auth=digest, headers={'Content-Type': 'text/xml; charset="utf-8"', 'SoapAction': action})
    msgurl = parseString(res.text).getElementsByTagName('NewURL')[0].firstChild.data
    res = requests.get(msgurl)
    return xmltodict.parse(res.text)["Root"]["Message"]

def setMark(fritzbox_ip, digest, index, mark):
    location = "/upnp/control/x_tam"
    (action, data) = soapXML('MarkMessage', 'urn:dslforum-org:service:X_AVM-DE_TAM:1', 
                            f'<NewIndex>0</NewIndex><NewMessageIndex>{index}</NewMessageIndex><NewMarkedAsRead>{mark}</NewMarkedAsRead>')
    url = f'http://{fritzbox_ip}:49000{location}'
    res = requests.post(url, data=data, auth=digest, headers={'Content-Type': 'text/xml; charset="utf-8"', 'SoapAction': action})
    return res


def getMsg(fritzbox_ip, sid, msg):
    url = f'http://{fritzbox_ip}/cgi-bin/luacgi_notimeout?{sid}&script=/lua/photo.lua&myabfile={msg["Path"].replace("/download.lua?path=","")}'
    res = requests.get(url)
    return res

def getSid(fritzbox_ip, digest):
    location = "/upnp/control/deviceconfig"
    (action, data) = soapXML('X_AVM-DE_CreateUrlSID', 'urn:dslforum-org:service:DeviceConfig:1')
    url = f'http://{fritzbox_ip}:49000{location}'
    res = requests.post(url, data=data, auth=digest, headers={'Content-Type': 'text/xml; charset="utf-8"', 'SoapAction': action})
    return parseString(res.text).getElementsByTagName('NewX_AVM-DE_UrlSID')[0].firstChild.data

def getMsgForIndex(fritzbox_ip, digest, index):
    msgs = list(filter(lambda msg: int(msg['Index'])==index, getTAM(fritzbox_ip, digest)))
    if len(msgs)!=1:
        print(f"No message with Index {index} found!")
        raise typer.Exit(code=1)
    return msgs[0]

@main.command("list")
def listMsg(username: str, password: str, fritzbox_ip: str = "fritz.box"):
    """Lists all available messages as json"""
    digest = HTTPDigestAuth(username, password)
    msgs = getTAM(fritzbox_ip, digest)
    print(msgs)

@main.command("get")
def getMsg(username: str, password: str, index: int, fritzbox_ip: str = "fritz.box"):
    """Fetches a single message identified by the index in the list"""
    digest = HTTPDigestAuth(username, password)
    msg = getMsgForIndex(fritzbox_ip, digest, index)
    sid = getSid(fritzbox_ip, digest)
    wav = getMsg(fritzbox_ip, sid, msg)
    filename = f'{msg["Date"]} - {msg["Number"]}.wav'
    file = open(filename, 'wb')
    file.write(wav.content)
    file.close()
    print(f'{filename}')

@main.command()
def mark(username: str, password: str, index: int, read: Annotated[Optional[bool], typer.Option("--read/--unread")]  = True, fritzbox_ip: str = "fritz.box"):
    """Marks a single message as read (default=True) or unread (False)"""
    digest = HTTPDigestAuth(username, password)
    msg = getMsgForIndex(fritzbox_ip, digest, index)
    newnew = 0 if read else 1
    if newnew == int(msg['New']):
        print("No change required")
        return
    result = setMark(fritzbox_ip, digest, index, 1-newnew)
    print(result.reason)
    #print("OK" if result.ok else f"Error: {result.reason}")
