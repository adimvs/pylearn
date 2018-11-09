# import the necessary packages
#from pyimagesearch.transform import four_point_transform
import numpy as np
import cv2
import imutils
from PIL import Image
import pytesseract
import re
import base64
import io
import http.client, urllib.request, urllib.parse, urllib.error, base64
from http.client import HTTPSConnection
import os
from flask import json, jsonify
import pymongo
from bson.objectid import ObjectId
from bson.json_util import dumps, loads
import time

import json
from bson import ObjectId

def handleConfirmationRequest(requestdata, existing_id, to_key):
    try:
        faceId1 = sendDetectRequest(requestdata)
        username = os.environ.get("USER")
        password = os.environ.get("PASS")
        myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
        mydb = myclient["peopledb"]
    
        mycol = mydb["identities"]
        
        myid = mycol.find_one({'_id': ObjectId(existing_id)})
        
        decoded = base64.decodebytes(myid['document_image'].encode('ascii'))
        faceId2 = sendDetectRequest(decoded)
        
        isIdentical = sendVerifyRequest(faceId1, faceId2)
        
        if isIdentical is True:
            myid['state'] = 'confirmed'
            x = mycol.replace_one({"_id": ObjectId(existing_id)}, myid)
            sendConfirmationNotification(to_key)
        else:
            change_state(existing_id, 'retry_selfie')
            sendNotConfirmedNotification(to_key)
#        time.sleep(6)
#         response = getMSResponse(operation_location)
#         parsed_response = iterateData(response["recognitionResult"])
#         person = save_identity(parsed_response,requestdata, existing_id)
#         print(person)
#         sendNotification(person)
    except Exception as e:
        print("[Errno {0}]".format(str(e)))
        sendFailedExtractionNotification(str(e), to_key)
        
def handleExtractionRequest(requestdata, existing_id, to_key):
    try:
        operation_location = sendMSRequest(requestdata)
        time.sleep(6)
        response = getMSResponse(operation_location)
        parsed_response = iterateData(response["recognitionResult"])
        person = save_identity(parsed_response,requestdata, existing_id,'pending')
        print(person)
        sendNotification(person)
    except Exception as e:
        # print("[Errno {0}] {1}".format(e.errno, e.strerror))
        change_state(existing_id, 'retry_doc')
        sendFailedExtractionNotification(str(e), to_key)

def change_state(existing_id, newstate):
    #mongodb:27017
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
  
    newvalues = { "$set": { "state": "%s" % newstate } }
    x = mycol.update_one({"_id": ObjectId(existing_id)}, newvalues)
    
    
def sendFailedExtractionNotification(message, to_key):
    api_key = os.environ.get("NOTIF_API_KEY")
    print(api_key)
    print(to_key)
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Authorization': '%s' % api_key,
    }
    print(headers)
    request_body = {
    # Request headers
    'to': '%s' % to_key,
    'collapse_key' : 'type_a',
    'notification' : {
    'body' : 'ID Extraction Failed! Please try again',
    'title': 'Attention!'
    },
    "data" : {
     "error" : "Nume:%s" % message
    }
    }
    
    try:
        conn = http.client.HTTPSConnection('fcm.googleapis.com')
        conn.request("POST", "/fcm/send", json.dumps(request_body), headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}] ".format(str(e)))
    
    return response.headers["Operation-Location"]               
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

def save_new_identity(person_identity):
    #mongodb:27017
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    x = mycol.insert_one(person_identity)
    print(person_identity)
    print(x.inserted_id)
    return str(x.inserted_id)    
def save_identity(person_identity,raw_image_data, existing_id, newstate):
    #mongodb:27017
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    myid = mycol.find_one({'_id': ObjectId(existing_id)})
    
    person_identity["to_key"] = myid['to_key']
        
    person_identity["document_image"] = base64.b64encode(raw_image_data).decode()
    person_identity['state'] = newstate
    person_identity['_id'] = ObjectId(existing_id)
    x = mycol.replace_one({"_id": ObjectId(existing_id)}, person_identity)
    
    return person_identity

def sendMSRequest(binaryImage):
    api_key = os.environ.get("MS_API_KEY")
    print(api_key)
    headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': '%s' % api_key,
    }
    print(headers)
    params = urllib.parse.urlencode({
        # Request parameters
        'mode': 'Printed',
    })
    
    try:
        conn = http.client.HTTPSConnection('westeurope.api.cognitive.microsoft.com')
        conn.request("POST", "/vision/v2.0/recognizeText?%s" % params, binaryImage, headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}] ".format(str(e)))
        raise
    
    return response.headers["Operation-Location"]
def sendVerifyRequest(faceId1,faceId2):
    api_key = os.environ.get("FACE_API_KEY")
    print(api_key)
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': '%s' % api_key,
    }
    print(headers)
    params = urllib.parse.urlencode({
    })
    request_body = {
    # Request headers
    'faceId1': '%s' % faceId1,
    'faceId2' : '%s' % faceId2
    }
    
    try:
        conn = http.client.HTTPSConnection('westeurope.api.cognitive.microsoft.com')
        conn.request("POST", "/face/v1.0/verify?%s" % params, json.dumps(request_body), headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        json_obj = json.loads(data)
        print(json_obj)
        isIdentical=json_obj['isIdentical']
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))
    
    return isIdentical
def sendDetectRequest(binaryImage):
    api_key = os.environ.get("FACE_API_KEY")
    print(api_key)
    headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': '%s' % api_key,
    }
    print(headers)
    params = urllib.parse.urlencode({
    # Request parameters
    'returnFaceId': 'true',
    'returnFaceLandmarks': 'false'
    })
    
    try:
        conn = http.client.HTTPSConnection('westeurope.api.cognitive.microsoft.com')
        conn.request("POST", "/face/v1.0/detect?%s" % params, binaryImage, headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        json_obj = json.loads(data)
        print(json_obj)
        faceId=json_obj[0]['faceId']
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))
    
    return faceId

def sendConfirmationNotification(to_key):
    api_key = os.environ.get("NOTIF_API_KEY")
    print(api_key)
    
    print(to_key)
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Authorization': '%s' % api_key,
    }
    print(headers)
    request_body = {
    # Request headers
    'to': '%s' % to_key,
    'collapse_key' : 'type_a',
    'notification' : {
    'body' : 'Your identity has been confirmed',
    'title': 'Congratulations'
    },
    "data" : {
     "body" : "Your identity has been confirmed",
     "title": 'Congratulations'
    }
    }
    print(json.dumps(request_body))
    try:
        conn = http.client.HTTPSConnection('fcm.googleapis.com')
        conn.request("POST", "/fcm/send", json.dumps(request_body), headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))

def sendNotConfirmedNotification(to_key):
    api_key = os.environ.get("NOTIF_API_KEY")
    print(api_key)
    
    print(to_key)
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Authorization': '%s' % api_key,
    }
    print(headers)
    request_body = {
    # Request headers
    'to': '%s' % to_key,
    'collapse_key' : 'type_a',
    'notification' : {
    'body' : 'Your identity has not been confirmed. Please retry with another selfie',
    'title': 'Attention!'
    },
    "data" : {
     "body" : "YYour identity has not been confirmed. Please retry with another selfie",
     "title": 'Attention!'
    }
    }
    print(json.dumps(request_body))
    try:
        conn = http.client.HTTPSConnection('fcm.googleapis.com')
        conn.request("POST", "/fcm/send", json.dumps(request_body), headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))     
def sendNotification(person):
    api_key = os.environ.get("NOTIF_API_KEY")
    print(api_key)
    to_key = person['to_key']
    print(to_key)
    headers = {
    # Request headers
    'Content-Type': 'application/json',
    'Authorization': '%s' % api_key,
    }
    print(headers)
    request_body = {
    # Request headers
    'to': '%s' % to_key,
    'collapse_key' : 'type_a',
    'notification' : {
    'body' : 'Nume:%s' % person["last_name"],
    'title': 'ID Extraction Complete %s' % str(person['_id'])
    },
    "data" : {
     "body" : "Nume:%s" % person["last_name"],
     "title": 'ID Extraction Complete',
     "last_name" : "%s" % person["last_name"],
     "first_name" : "%s" % person["first_name"],
     "series" : "%s" % person["series"],
     "number" : "%s" % person["number"],
     "_id" : "%s" % str(person['_id'])
    }
    }
    print(json.dumps(request_body))
    try:
        conn = http.client.HTTPSConnection('fcm.googleapis.com')
        conn.request("POST", "/fcm/send", json.dumps(request_body), headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))
        raise
    
    return response.headers["Operation-Location"]

def getMSResponse(op_location):
    api_key = os.environ.get("MS_API_KEY")
    headers = {
    # Request headers
    'Ocp-Apim-Subscription-Key': '%s' % api_key,
    }

    params = urllib.parse.urlencode({
    })
    print(op_location.rsplit('/', 1)[1])
    try:
        conn = http.client.HTTPSConnection('westeurope.api.cognitive.microsoft.com')
        conn.request("GET", "/vision/v2.0/textOperations/%s" % op_location.rsplit('/', 1)[1], "", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        json_obj = json.loads(data)
        print(json_obj)
        conn.close()
    except Exception as e:
        print("[Errno {0}]".format(str(e)))
        raise
    return json_obj
def getEmptyPerson():
    person = {'first_name': '',
     'last_name': '',
     'series': '',
     'number': '',
     'cnp': '',
     'document_image':'',
     'selfie_image': '',
     'state':'',
     'to_key':''
    }
    return person

def getPersonById(p_id):
    person = {'first_name': '',
     'last_name': '',
     'series': '',
     'number': '',
     'cnp': '',
     'document_image':'',
     'selfie_image': '',
     'state':'',
     'to_key':'',
     '_id':''
    }
    
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    myid = mycol.find_one({'_id': ObjectId(p_id)})
    x = str(myid['_id'])
    myid['_id'] = x
    return myid
    
def iterateData(data):
    person = {'first_name': '',
     'last_name': '',
     'series': '',
     'number': '',
     'cnp': '',
     'document_image':'',
     'selfie_image': '',
     'state':''
    }
    
    for (k, v) in data.items():
        print("Key: " + k)
        print("Value: " + str(v))
        for line in v:
            print(line['text'])
            cnp_line = line['text'].find('CNP')
            if cnp_line>=0:
                print("--->")
                cnp = line['words'][1]['text']
                print(cnp)
                person['cnp'] = cnp
            name_line = line['text'].find('Nume')
            if name_line>=0:
                print("--->")
                name = v[v.index(line)+2]['words'][0]['text']
                #name = list(data)[tuple(data.keys()).index(k)+2]['words'][0]['text']
                print(name)
                person['last_name'] = name
            fname_line = line['text'].find('Prenume')
            if fname_line>=0:
                print("--->")
                fname = v[v.index(line)+1]['words'][0]['text']
                #name = list(data)[tuple(data.keys()).index(k)+2]['words'][0]['text']
                print(fname)
                person['first_name'] = fname
            seria_line = line['text'].find('SERIA')
            if seria_line>=0:
                print("--->")
                seria_line = line['words'][1]['text']
                #name = list(data)[tuple(data.keys()).index(k)+2]['words'][0]['text']
                print(seria_line)
                person['series'] = seria_line
            number_line = line['text'].find('NR')
            if number_line>=0:
                print("--->")
                number_line = line['words'][3]['text']
                #name = list(data)[tuple(data.keys()).index(k)+2]['words'][0]['text']
                print(number_line)
                person['number'] = number_line
    
    if is_empty(person['last_name']) or is_empty(person['first_name']) or is_empty(person['series']) or is_empty(person['cnp']) or is_empty(person['number']):
        raise Exception('Unable to extract data from document')
    return person

def is_empty(any_structure):
    if any_structure:
        print('Structure is not empty.')
        return False
    else:
        print('Structure is empty.')
        return True     

def stringToRGB(base64_string):
    imgdata = base64.b64decode(str(base64_string))
    image = Image.open(io.BytesIO(imgdata))
    return cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)

def byteToRGB(rawimg):
    image = Image.open(io.BytesIO(rawimg))
    return cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)

