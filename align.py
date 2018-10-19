# import the necessary packages
#from pyimagesearch.transform import four_point_transform
from skimage.filters import threshold_local
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
from flask import json

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
        conn = http.client.HTTPSConnection('westcentralus.api.cognitive.microsoft.com')
        conn.request("POST", "/vision/v2.0/recognizeText?%s" % params, binaryImage, headers)
        response = conn.getresponse()
        data = response.read()
        print(data)
        print(response.headers)
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))
    
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
        conn = http.client.HTTPSConnection('westcentralus.api.cognitive.microsoft.com')
        conn.request("GET", "/vision/v2.0/textOperations/%s" % op_location.rsplit('/', 1)[1], "", headers)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        json_obj = json.loads(data)
        print(json_obj)
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))
    return json_obj

def iterateData(data):
    person = {'first_name': '',
     'last_name': '',
     'series': '',
     'number': '',
     'cnp': ''}
    
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
                person['first_name'] = name
    return person
        
def extractIdData(image):
    person = {'first_name': 'Bill',
     'last_name': 'Gates',
     'series': 'RX',
     'number': '234987',
     'cnp': '1600011223344'}
    
    # load the image and compute the ratio of the old height
    # to the new height, clone it, and resize it
    ratio = image.shape[0] / 1000.0
    orig = image.copy()
    image = imutils.resize(image, height = 1000)
    
    # convert the image to grayscale, blur it, and find edges
    # in the image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)
     
    # show the original image and the edge detected image
    print("STEP 1: Edge Detection")
    #cv2.imshow("Image", image)
    #cv2.imshow("Edged", edged)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()
    
    # find the contours in the edged image, keeping only the
    # largest ones, and initialize the screen contour
    cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:5]
     
    # loop over the contours
    for c in cnts:
        # approximate the contour
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
     
        # if our approximated contour has four points, then we
        # can assume that we have found our screen
        if len(approx) == 4:
            screenCnt = approx
            break
    
    # show the contour (outline) of the piece of paper
    print("STEP 2: Find contours of paper")
    cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)
    
    # apply the four point transform to obtain a top-down
    # view of the original image
    warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)
     
    # convert the warped image to grayscale, then threshold it
    #--------------------
    # to give it that 'black and white' paper effect
    warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    T = threshold_local(warped, 21, offset = 30, method = "median")
    warped = (warped > T).astype("uint8") * 255
    #-----------------------------
    
     
    # show the original and scanned images
    print("STEP 3: Apply perspective transform")    
    
    print("STEP 4 Extract text")
    tmpimg = imutils.resize(warped,height=873, width=1239)
    #im = tmpimg[170:210,445:735]
    im_cnp = tmpimg[170:220,445:745]
    text_cnp = pytesseract.image_to_string(im_cnp)
    print(text_cnp)
    #text_all = pytesseract.image_to_string(tmpimg)
    p_cnp = re.compile("^[12]\d{12}")
    m_cnp = p_cnp.search(text_cnp)
    if m_cnp:
        cnp = m_cnp.group(0)
        person["cnp"] = cnp
        print(cnp)
    print("--")
    #im_name = tmpimg[240:286,385:600]
    im_name = tmpimg[220:300,385:600]
    text_name = pytesseract.image_to_string(im_name)
    p_name = re.compile("[A-Z]{3,}[A-Z]*")
    print(text_name)
    m_name = p_name.search(text_name)
    if m_name:
        name = m_name.group(0)
        person["first_name"] = name
        print(name)
    return person

def stringToRGB(base64_string):
    imgdata = base64.b64decode(str(base64_string))
    image = Image.open(io.BytesIO(imgdata))
    return cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)

def byteToRGB(rawimg):
    image = Image.open(io.BytesIO(rawimg))
    return cv2.cvtColor(np.array(image), cv2.COLOR_BGR2RGB)

def order_points(pts):
    # initialzie a list of coordinates that will be ordered
    # such that the first entry in the list is the top-left,
    # the second entry is the top-right, the third is the
    # bottom-right, and the fourth is the bottom-left
    rect = np.zeros((4, 2), dtype = "float32")
 
    # the top-left point will have the smallest sum, whereas
    # the bottom-right point will have the largest sum
    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
 
    # now, compute the difference between the points, the
    # top-right point will have the smallest difference,
    # whereas the bottom-left will have the largest difference
    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
 
    # return the ordered coordinates
    return rect

def four_point_transform(image, pts):
    # obtain a consistent order of the points and unpack them
    # individually
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
 
    # compute the width of the new image, which will be the
    # maximum distance between bottom-right and bottom-left
    # x-coordiates or the top-right and top-left x-coordinates
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
 
    # compute the height of the new image, which will be the
    # maximum distance between the top-right and bottom-right
    # y-coordinates or the top-left and bottom-left y-coordinates
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
 
    # now that we have the dimensions of the new image, construct
    # the set of destination points to obtain a "birds eye view",
    # (i.e. top-down view) of the image, again specifying points
    # in the top-left, top-right, bottom-right, and bottom-left
    # order
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype = "float32")
 
    # compute the perspective transform matrix and then apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
 
    # return the warped image
    return warped

