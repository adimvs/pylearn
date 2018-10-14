from flask import Flask, jsonify

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
@app.route('/api/v1/resources/idcards/extract', methods=['GET','POST'])
def api_all():
    return jsonify(person)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=8080)
