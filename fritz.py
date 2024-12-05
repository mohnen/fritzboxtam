import requests
from requests.auth import HTTPDigestAuth

from xml.dom.minidom import parseString

import xmltodict

boxIP = "fritz.box"
boxUser = "home-assistant"
boxPW = "0xcafebabe"

def soapXML(action, uri, args=""):
    soapAction = f'{uri}#{action}'
    soapData = f"<?xml version='1.0' encoding='utf-8'?><s:Envelope s:encodingStyle='http://schemas.xmlsoap.org/soap/encoding/' xmlns:s='http://schemas.xmlsoap.org/soap/envelope/'><s:Body><u:{action} xmlns:u='{uri}'>{args}</u:{action}></s:Body></s:Envelope>"
    return (soapAction, soapData)

def getTAM(box, digest):
    location = "/upnp/control/x_tam"
    (action, data) = soapXML('GetMessageList', 'urn:dslforum-org:service:X_AVM-DE_TAM:1', '<NewIndex>0</NewIndex>')
    url = f'http://{boxIP}:49000{location}'
    res = requests.post(url, data=data, auth=digest, headers={'Content-Type': 'text/xml; charset="utf-8"', 'SoapAction': action})
    msgurl = parseString(res.text).getElementsByTagName('NewURL')[0].firstChild.data
    res = requests.get(msgurl)
    return xmltodict.parse(res.text)["Root"]["Message"]

def getMsg(sid, msg):
    url = f'http://{boxIP}/cgi-bin/luacgi_notimeout?{sid}&script=/lua/photo.lua&myabfile={msg["Path"].replace("/download.lua?path=","")}'
    res = requests.get(url)
    return res

def getSid(box, digest):
    location = "/upnp/control/deviceconfig"
    (action, data) = soapXML('X_AVM-DE_CreateUrlSID', 'urn:dslforum-org:service:DeviceConfig:1')
    url = f'http://{boxIP}:49000{location}'
    res = requests.post(url, data=data, auth=digest, headers={'Content-Type': 'text/xml; charset="utf-8"', 'SoapAction': action})
    return parseString(res.text).getElementsByTagName('NewX_AVM-DE_UrlSID')[0].firstChild.data

digest = HTTPDigestAuth(boxUser, boxPW)
msgs = getTAM(boxIP, digest)
sid = getSid(boxIP, digest)
msg = getMsg(sid, msgs[0])
file = open('message.wav', 'wb')
file.write(msg.content)
file.close()
