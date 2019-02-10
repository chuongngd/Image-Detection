from flask import Flask, render_template, request, url_for, redirect
from flask import session
from dbconnect import connection
from wtforms import Form, BooleanField, TextField, PasswordField, validators
from passlib.hash import sha256_crypt
from object_detection.object_detection.object_detection_api_example import get_objects
from object_detection.object_detection.object_detection_api_example import detectImageDraw
from PIL import Image
import base64
import io
import os
from os.path import join
from matplotlib import pyplot as plt
from DAO import DAO

app = Flask(__name__, static_folder = "images")
#app = Flask(__name__)

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
    email = TextField('Email address',[validators.Length(min=6,max=50),validators.DataRequired()])
    firstname = TextField('First name', [validators.Length(min=2, max=50),validators.DataRequired()])
    lastname = TextField('Last name', [validators.Length(min=2, max=50),validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])

    
#register function
@app.route('/register/', methods=["GET", "POST"])
def register_page():
    form = RegistrationForm(request.form)
    # check if there is request method to register, get the user information and execute mysql statement to insert database
    if request.method == "POST" and form.validate():
        #get data from input form
        username = form.username.data
        email = form.email.data
        firstname = form.firstname.data
        lastname = form.lastname.data
        password = form.password.data
        user = DAO.checkUsername(username)
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

def read_file(filename):
    with open(filename, 'rb') as f:
        photo = f.read()
    return photo  
import random
@app.route ('/uploadimage/')
def uploadimage():
    return render_template("home.html")
@app.route('/upload/',methods=["GET","POST"])
def upload():    
    c,conn = connection()
    #request upload file from browser
    file = request.files['image']
    #read file
    data = file.read()
    #get the file name
    fullFilename = file.filename
    #open file under image type
    image=Image.open(file)
    #create a list of objects 
    objects={}
    #call the get_objects function from object detection api to get all objects of the image
    objects = get_objects(image)  
    #extract the file name and the extension of the image
    filename = os.path.splitext(fullFilename)[0]
    #extension
    ext = os.path.splitext(fullFilename)[-1]
    #rename the file name to avoid duplicate file name in database
    imagename = DAO.checkImageName(fullFilename)
    if(imagename):
        fullFilename = filename + str(random.randint(1,21)*5) + ext
    DAO.insertImage(fullFilename,data,str(objects))
    #get the number of objects in the image by retrieve the JSON array numObjects property
    a = objects["array"][0]['numObjects']
    #for each of object from image, insert its properties into objects table
    for i in range(1,a+1):
        DAO.insertObjects(fullFilename,objects["array"][i]['class_name'],objects["array"][i]['score'],
                          objects["array"][i]['x'],objects["array"][i]['y'],objects["array"][i]['width'],
                          objects["array"][i]['height'])

    #call the object detection api function to detect and draw the object box
    #the image after draw will be saved in localhost
    detectImageDraw(image,fullFilename)
  
    #open the image after draw object box
    with open(os.path.join(app.config['UPLOAD_FOLDER'], fullFilename),'rb') as f:
        detect_image_data= f.read()
    
    #update the mysql images table, insert the image after detection into mysql images table 
    DAO.updateImage(detect_image_data,fullFilename)
    
    #display photo from mysql before detection
    record = DAO.retrievePhoto(fullFilename)
    
    databaseImage = base64.b64encode(record[0])
    #display photo from mysql after detection
    newrecord = DAO.retrievePhotoDetection(fullFilename)
    
    newdatabaseImage = base64.b64encode(newrecord[0])
   
    return render_template("uploadimage.html", databaseImage = databaseImage.decode('ascii'),
                           newdatabaseImage = newdatabaseImage.decode('ascii'), objects = objects, image_name=fullFilename)

#using wtforms to build the search form validate input data
class searchInputForm(Form):
    search = TextField('search',[validators.Length(min=4,max=20), validators.DataRequired()])


@app.route('/searchImage/', methods=["GET", "POST"])
def searchImage():
    form = searchInputForm(request.form)
    if request.method == "POST":
        #get the search input data
        searchObject = form.search.data
        # call the DAO function to search all images name which contain the object from mysql, it will return a list of images name
        record = DAO.searchImageNameFromObject(searchObject)
        #if there is no image
        if record == 0:
            message = "There is no image contains this object"
            return render_template('searchImageNoFound.html',form = form, message = message)
        # convert list of image name to array of images name
        list_image_name = []
        for index in range(len(record)):
            list_image_name.append(record[index][0])
        #remove duplicate image
        imagelist = list(dict.fromkeys(list_image_name))
        #create an array to contain the original photos of searching object
        photo = []
        #create an array to contain the detection photos of searching object
        newphoto = []
        #with each image name corresponding with the searching object, retrieve photo data by the image name from mysql and put in a list
        for index in range(len(imagelist)):
            photodata = DAO.retrievePhoto(imagelist[index])
            databaseImage = (base64.b64encode(photodata[0])).decode('ascii')
            photo.append(databaseImage)
        for index in range(len(imagelist)):
            newrecordphoto = DAO.retrievePhotoDetection(imagelist[index])
            newdatabaseImage = (base64.b64encode(newrecordphoto[0])).decode('ascii')
            newphoto.append(newdatabaseImage)
     
        #return template with a list of photos contain searching object in original and deteection format
        return render_template("searchImageResult.html", photo = photo, newphoto = newphoto, object = searchObject)
    return render_template('searchImage.html',form = form)
    
if __name__ == "__main__":
    app.debug = True
    app.run()
