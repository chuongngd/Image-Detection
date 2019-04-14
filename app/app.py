from flask import Flask, render_template, request, url_for, redirect, Response, jsonify
from flask import session
from dbconnect import connection
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from object_detection.object_detection.object_detection_api_example import get_objects
from object_detection.object_detection.object_detection_api_example import detect_image_draw
from object_detection.object_detection.object_detection_api_example import detect_image_draw_one_object
from object_detection.object_detection.object_detection_api_example import detect_video

from object_detection.object_detection.object_detection_api_example import search_video

from PIL import Image
import base64
import io
import os
from os.path import join
from matplotlib import pyplot as plt
from DAO import DAO
import json
import numpy as np
import random
app = Flask(__name__, static_folder = "static")

#import logging library to create logger file 'errorlog.txt' to log messages for the application
from logging import FileHandler, DEBUG
file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(DEBUG)
app.logger.addHandler(file_handler)

app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PHOTOS_FOLDER = os.path.join('images')
app.config['UPLOAD_FOLDER'] =PHOTOS_FOLDER

@app.route('/')
def home():
    return render_template("home.html")
#function login
@app.route('/login/',methods = ['POST', 'GET'])
def login():
    #check if there is request method to login, get the user information and execute mysql statement to log in
   if request.method == 'POST':
      username = request.form['username']
      password = request.form['password']
      login = DAO.login(username,password)  
      if login == False:
          message = "Wrong username or password"
          return render_template('login.html', message=message)
      #otherwise redirect to home page of application
      else:
          session['name'] = username
          return render_template('home.html')
    #if there is not request method, show the login page
   else:
       return render_template('login.html')

#log out and delete the user session
@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return render_template("home.html")

#using wtforms to build the registration form validate input data
class RegistrationForm(Form):
    username = TextField('Username',[validators.Length(min=4,max=20), validators.DataRequired()])
    email = TextField('Email address',[validators.DataRequired()])
    firstname = TextField('First name', [validators.Length(min=2, max=50),validators.DataRequired()])
    lastname = TextField('Last name', [validators.Length(min=2, max=50),validators.DataRequired()])
    password = PasswordField('Password', [validators.Length(min=6,max=50),validators.DataRequired()])

    
#register function
@app.route('/register/', methods=["GET", "POST"])
def register():
    form = RegistrationForm(request.form)
    # check if there is request method to register, get the user information and execute mysql statement to insert database
    if request.method == "POST" and form.validate():
        #get data from input form
        username = form.username.data
        email = form.email.data
        firstname = form.firstname.data
        lastname = form.lastname.data
        password = form.password.data
        user = DAO.check_username(username)
        if user:
            message = "That username is already taken, please choose another"
            return render_template('register.html', form=form, message = message)
        #if not, insert new user information to database
        else:
           
            register = DAO.register(username,password,email,firstname,lastname)
            if register == True:
                session['name'] = username
                return redirect(url_for('home'))
    # if there is not request method, or input data don't meet requirements, show the register page
    return render_template("register.html", form=form)

#function to open and read a file
def read_file(filename):
    with open(filename, 'rb') as f:
        photo = f.read()
    return photo  

#define render template for a url 
@app.route ('/uploadimage/')
def uploadimage():
    return render_template("home.html")

# function convert an image to numpy array
def load_image_into_numpy_array(image):
  (im_width, im_height) = image.size
  return np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)

#function to execute image upload. 
#Then the function get_objects from object detection api will extract all objects from the image
#A new image with draw box around the extracted object will be draw 
#The function return render template display origial image and a new image with draw object
#Both original image and new image with draw bouding box will be saved in database
@app.route('/upload/',methods=["GET","POST"])
def upload():    
    c,conn = connection()
    #request upload file from browser
    file = request.files['image']
    
    #get the file name
    full_filename = file.filename
    
    #extract the file name and the extension of the image
    filename = os.path.splitext(full_filename)[0]
    #extension
    ext = os.path.splitext(full_filename)[-1]
    
    #rename the file name to avoid duplicate file name in database
    imagename = DAO.check_image_name(full_filename)
    if(imagename):
        full_filename = filename + str(random.randint(1,21)*5) + ext
    #save the imae into local
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], "original_" + full_filename ))
    file.seek(0)
    #read file
    data = file.read()
    #get the file name 
    #fullFilename = full_name_original
    #open file under image type
    image=Image.open(file)
    #create a list of objects 
    objects={}
    #call the get_objects function from object detection api to get all objects of the image
    objects = get_objects(image)  
    DAO.insert_image(full_filename,data,str(objects))
    #get the number of objects in the image by retrieve the JSON array numObjects property
    a = objects["array"][0]['numObjects']
    #for each of object from image, insert its properties into objects table
    for i in range(1,a+1):
        DAO.insert_objects(full_filename,objects["array"][i]['class_name'],objects["array"][i]['score'],
                          objects["array"][i]['x'],objects["array"][i]['y'],objects["array"][i]['width'],
                          objects["array"][i]['height'])

    #call the object detection api function to detect and draw the object box
    #the image after draw will be saved in localhost
    detect_image_draw(image,full_filename)
  
    #open the image after draw object box
    with open(os.path.join(app.config['UPLOAD_FOLDER'], full_filename),'rb') as f:
        detect_image_data= f.read()
    
    #update the mysql images table, insert the image after detection into mysql images table 
    DAO.update_image(detect_image_data,full_filename)
    
    #display photo from mysql before detection
    databaseImage = base64.b64encode(data)
    
    #display photo from mysql after detection
    newrecord = DAO.retrieve_photo_detection(full_filename)
    newdatabaseImage = base64.b64encode(newrecord[0])
    objectlist  = []
    for i in range(1,a+1):
        objectlist.append(objects["array"][i]['class_name'])  
    
    #remove duplicate image
    list_objects = list(dict.fromkeys(objectlist))
    list_objects_string = ''.join(map(str,list_objects))
    
    return render_template("uploadimage.html", databaseImage = databaseImage.decode('ascii'),
                           newdatabaseImage =  newdatabaseImage.decode('ascii'), objects = objects, image_name=full_filename, list_objects = list_objects, list_objects_string  = list_objects_string )

#function to display the image with draw box on a specific object
@app.route('/viewobject/', methods = ['GET','POST'])
def viewobject():
    
    if request.method == 'POST':
        #request data from post method
        data = json.loads(request.data)
        #get image name
        image_name = data['image_name']
        #get specific object name to draw bouding box
        name = data['name']
        #get list of objects
        objects = data['objects']
        list_objects =  eval(objects,{'__buitins__':None},{})
        #convert the list of objects from image to a string
        list_objects_string = str(objects)
        
        #open the original image from local
        original_image_data = Image.open(os.path.join(app.config['UPLOAD_FOLDER'],"original_" + image_name))
        
        #call the object detection api to draw only the object which pass from template
        detect_image_draw_one_object(original_image_data,name,image_name)
        
        #display the image with bouding box on the specific object
        with open(os.path.join(app.config['UPLOAD_FOLDER'], name + "_" + image_name),'rb') as f:
            single_object_image_data= f.read()
        single_image = base64.b64encode(single_object_image_data)
        
        return render_template("viewSingleObject.html", single_image = single_image.decode('ascii'), list_objects_string = list_objects_string, image_name = image_name, list_objects = list_objects, name = name)
    else:
        return render_template('home.html')
    
#function to draw the other objects in the image after draw the first object
@app.route('/viewsecondobject/', methods = ['GET','POST'])
def viewsecondobject():
    
    if request.method == 'POST':
        #request data from post method
        image_name = request.form['image_name']
        name = request.form['object']
        list_objects_string = request.form['list_objects_string']
        list_objects = eval(list_objects_string)
        #open the original image from local
        original_image_data = Image.open(os.path.join(app.config['UPLOAD_FOLDER'],"original_" + image_name))
        #call the object detection api to draw only the object which pass from template
        detect_image_draw_one_object(original_image_data,name,image_name)
        #display the image with bouding box on the specific object
        with open(os.path.join(app.config['UPLOAD_FOLDER'], name + "_" + image_name),'rb') as f:
            single_object_image_data= f.read()
        single_image = base64.b64encode(single_object_image_data)
        
        return render_template("viewSecondObject.html", single_image = single_image.decode('ascii'),  list_objects_string  =  list_objects_string, list_objects = list_objects, image_name = image_name, name = name)
        
    else:
        return render_template('home.html')
    
#using wtforms to build the search form validate input data
class search_input_form(Form):
    search = TextField('search',[validators.Length(min=4,max=20), validators.DataRequired()])


@app.route('/searchImage/', methods=["GET", "POST"])
def search_image():
    form = search_input_form(request.form)
    if request.method == "POST":
        #get the search input data
        search_object = form.search.data
        # call the DAO function to search all images name which contain the object from mysql, it will return a list of images name
        record = DAO.search_image_name_from_object(search_object)
        #if there is no image
        if record == 0:
            message = "There is no image contains this object"
            return render_template('searchImageNoFound.html',form = form, message = message)
        # convert list of image name to array of images name
        list_image_name = []
        for index in range(len(record)):
            list_image_name.append(record[index][0])
        #remove duplicate image
        image_list = list(dict.fromkeys(list_image_name))
        #create an array to contain the original photos of searching object
        photo = []
        #create an array to contain the detection photos of searching object
        newphoto = []
        #with each image name corresponding with the searching object, retrieve photo data by the image name from mysql and put in a list
        for index in range(len(image_list)):
            photo_data = DAO.retrieve_photo(image_list[index])
            database_image = (base64.b64encode(photo_data[0])).decode('ascii')
            photo.append(database_image)
        for index in range(len(image_list)):
            newrecord_photo = DAO.retrieve_photo_detection(image_list[index])
            newdatabase_image = (base64.b64encode(newrecord_photo[0])).decode('ascii')
            newphoto.append(newdatabase_image)
     
        #return template with a list of photos contain searching object in original and deteection format
        return render_template("searchImageResult.html", photo = photo, newphoto = newphoto, object = search_object)
    return render_template('searchImage.html',form = form)
  
#function to search an object from video capture
@app.route('/searchVideoCapture/', methods=["GET", "POST"])
def search_video_capture():
    form = search_input_form(request.form)
    if request.method == "POST":
        #get the search input data
        search_object = form.search.data
        # call the DAO function to search all images name which contain the object from mysql, it will return a list of images name
        records = DAO.search_image_from_videocapture(search_object)
        if records == 0:
            message = "There is no video capture contains this object"
            return render_template('searchImageNoFound.html',form = form, message = message)
        #if there is no image
        photo = []
        time = records[1]
        for index in range(len(records[0])):
            #photo_data = DAO.retrieve_photo(image_list[index])
            database_image = (base64.b64encode(records[0][index])).decode('ascii')
            photo.append(database_image)
            time.append(records[1][index])
        length = len(records[0])
        #return template display all the images with captrue time
        return render_template("searchVideoCaptureResult.html",photo = photo, time = time, length = length, search_object = search_object)
    return render_template('searchVideoCapture.html',form = form)

#function to display video streaming detection
@app.route('/video')
def video():
    """Video streaming home page."""
    return render_template('video.html')
       
#function to stop video streaming detection
@app.route('/stopstream',methods=['GET', 'POST'])
def stop_stream():
    import cv2
    cap = cv2.VideoCapture(0)
    while(cap.isOpened()):
        break
    cv2.destroyAllWindows()
    cap.release()
    return render_template('home.html')

#function support video streaming
@app.route('/video_viewer')
def video_viewer():
    return Response(detect_video(),mimetype='multipart/x-mixed-replace; boundary=frame')
 
#function to get the input object and search the object on the live stream detection
@app.route('/searchresult',methods=['GET', 'POST'])
def searchresult():
    objectname = ""
    if request.method == "POST":
        objectname = request.form["objectname"]
    return render_template('searchresult.html',objectname = objectname)

#function return streaming video without searched object
@app.route('/searchvideo/')
def searchempty():
    return Response(detect_video(),mimetype='multipart/x-mixed-replace; boundary=frame')

#function to pass a specific object as a argument and display it on the streaming video and display it
@app.route('/searchvideo/<objectname>')
def searchvideo(objectname):
    return Response(search_video(objectname),mimetype='multipart/x-mixed-replace; boundary=frame')

#function to reder the template for searching multiple images
@app.route ('/findimage/')
def find_image():
    return render_template("findImages.html")

#function to find the images that contain one or many input objects from multiple images
@app.route('/findimageresult/', methods = ['GET','POST'])
def find_image_result():
   
    result_list=[]
    image_list = []
    #get the search object from request form
    objectname = request.form["objectname"]
    
    #get the multiple images from request form
    for file in request.files.getlist("image") :
        #get all the objects of each image
        data = file.read()
        image=Image.open(file)
        file.seek(0)
        objects = get_objects(image) 
        a = objects["array"][0]['numObjects']
        objectlist  = []
        objectname_list=[]
        
        for i in range(1,a+1):
            objectlist.append(objects["array"][i]['class_name'])
        #remove duplicate objects from an image list
        objectlist = list(dict.fromkeys(objectlist))
        #sort the image list
        objectlist.sort()
        #convert the image list to string name of image
        objects_string = ','.join(map(str,objectlist))
        #if the input search object is more than on object, separated by commas 
        #convert it to a list and compare to the objectlist
        #if the search objects are in the objectlist, put the image in to an image list
        if ',' in objectname:
            objectname_list = objectname.split(',')
            objectname_list.sort()
            if set(objectname_list).issubset(objectlist):
                result_list.append(objectlist)         
                data_image = base64.b64encode(data)
                image_list.append(data_image.decode('ascii'))
        else:
            #if the input search object is only one object
            #compare if the search object is in the object string
            #then put the image into an image list if the search object is in the object string
            if objectname in objects_string:
                result_list.append(objectlist) 
                data_image = base64.b64encode(data)
                image_list.append(data_image.decode('ascii'))
                
    #pass the image list to the template and display
    if image_list == []:
        return render_template('findImageResultNotFound.html',objectname_list = objectname_list, objects_string = objects_string,  objectlist = result_list, objectname = objectname)
    else:
        return render_template('findImageResult.html',objects_string  = objects_string, objectlist = result_list, objectname = objectname, image_list = image_list)



if __name__ == "__main__":
    app.debug = True
    app.run()
