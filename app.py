from flask import Flask, jsonify, request, json
from align import stringToRGB, extractIdData, byteToRGB, sendMSRequest,\
    getMSResponse, iterateData
import time
app = Flask(__name__)

person = {'first_name': 'Bill',
     'last_name': 'Gates',
     'series': 'RX',
     'number': '234987',
     'cnp': '1600011223344'}

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
    return jsonify(parsed_response)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080)
