from flask import Flask, jsonify, request, json
from align import stringToRGB, extractIdData, byteToRGB, sendMSRequest,\
    getMSResponse, iterateData, sendNotification, JSONEncoder, handleExtractionRequest, getEmptyPerson,\
    save_new_identity
import time
import pymongo
import os
from bson.objectid import ObjectId
from bson.json_util import dumps, loads
import threading
import copy

app = Flask(__name__)

person = {'first_name': 'Bill',
     'last_name': 'Gates',
     'series': 'RX',
     'number': '234987',
     'cnp': '1600011223344'}

person_identity = {'first_name': 'Bill',
     'last_name': 'Gates',
     'series': 'RX',
     'number': '234987',
     'cnp': '1600011223344',
     'document_image':'',
     'selfie_image':''}

@app.route("/")
def hello_world():
    return "Hello World!"

# A route to return all of the available entries in our catalog.
@app.route('/api/v1/resources/idcards/test', methods=['GET','POST'])
def api_all():
    content = request.json
    print(content)
    #image = stringToRGB(content["imageBase64"])
    image = byteToRGB(request.data)
    person = extractIdData(image)
    return jsonify(person)

# A route to return all of the available entries in our catalog.
@app.route('/api/v1/resources/idcards/extract', methods=['GET','POST'])
def api_test():
    existing_id = request.headers.get("EXISTING_ID")
    to_key = request.headers.get("TO_KEY")
    
    if existing_id is None:
        #we have new identity
        p = getEmptyPerson()
        p['state'] = 'new'
        p['to_key'] = to_key
        existing_id = save_new_identity(p)
        p['id'] = existing_id
    reqdata = request.data[:]
    print(type(request.data))
    processing_thread = threading.Thread(target=handleExtractionRequest, args=(reqdata, existing_id))
    processing_thread.start()
    print(p)
    return jsonify(p)

# A route to return all of the available identities in our catalog.
@app.route('/api/v1/resources/identities/<res_id>', methods=['GET'])
def get_id_by_id(res_id):
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    myid = mycol.find_one({'_id': ObjectId(res_id)})

    json_string = JSONEncoder().encode(myid)
    print(json_string)
    #back_to_dict = loads(json_string)
    
    return json_string

# A route save a new identity.
@app.route('/api/v1/resources/identities', methods=['POST'])
def save_id():
    #mongodb:27017
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/peopledb" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    x = mycol.insert_one(person_identity)
    
    print(x.inserted_id)
    
    response = {'id': '%s' % x.inserted_id}
    return jsonify(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080)
