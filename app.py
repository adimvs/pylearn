from flask import Flask, jsonify, request, json
from align import stringToRGB, extractIdData, byteToRGB, sendMSRequest,\
    getMSResponse, iterateData, sendNotification
import time
import pymongo
import os

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
    operation_location = sendMSRequest(request.data)
    time.sleep(6)
    response = getMSResponse(operation_location)
    parsed_response = iterateData(response["recognitionResult"])
    sendNotification(parsed_response)
    return jsonify(parsed_response)

# A route to return all of the available identities in our catalog.
@app.route('/api/v1/resources/identities', methods=['GET'])
def get_id_by_id():
    res_id = request.url.rsplit('/', 1)[1]
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    myid = mycol.find_one({'_id': ObjectId(res_id)})

    
    return jsonify(myid)

# A route save a new identity.
@app.route('/api/v1/resources/identities', methods=['POST'])
def save_id():
    #mongodb:27017
    username = os.environ.get("USER")
    password = os.environ.get("PASS")
    myclient = pymongo.MongoClient("mongodb://%s:%s@mongodb:27017/" % (username,password))
    mydb = myclient["peopledb"]

    mycol = mydb["identities"]
    
    x = mycol.insert_one(person_identity)
    
    print(x.inserted_id)
    
    response = {'id': '%s' % x.inserted_id}
    return jsonify(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080)