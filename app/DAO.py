from dbconnect import connection

import mysql.connector
class DAO:
   
    def login(username, password):
        try:
            c, conn = connection()
            c.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username,password,))
            user = c.fetchone()
            if not user:
                c.close()
                conn.close()
                return False
            else:
                c.close()
                conn.close()
                return True
        except mysql.connector.Error as error:
            conn.rollback()
            print("Failed searching username and password in database {}".format(error))
    
    def checkUsername(username):
        try:
            c,conn = connection()
            c.execute("SELECT * FROM users WHERE username = %s",(username,))
            user = c.fetchone()
            if user:
                c.close()
                conn.close()
                return True
            else:
                c.close()
                conn.close()
                return False
        except mysql.connector.Error as error:
            conn.rollback()
            print("Failed searching username in database {}".format(error))
    def register(username, password, email, firstname, lastname):
        try:
            c,conn = connection()
            sql = "INSERT INTO users (username, password, email, firstname,lastname) VALUES (%s, %s, %s, %s, %s)"
            val = (username, password, email, firstname, lastname)
            c.execute(sql, val)
            conn.commit()
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed inserting data into MySQL table {}".format(error))
        finally:
            c.close()
            conn.close()
            return True
        
    def checkImageName(imagename):
        try:
            c,conn = connection()
            sql = "SELECT * FROM images WHERE imagename = %s"
            val = (imagename,)
            c.execute(sql,val)
            count = c.rowcount
            if(count>0):
                return True
            else:
                return False
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed searching data in MySQL table {}".format(error))
    
    #insert into images table value of an image, include imagename, objects under JSON type, photo data under BLOB type
    def insertImage(filename, data, objects):
        try:
            c,conn = connection()
            sql = "INSERT INTO images (imagename, photo,objects) VALUES (%s, %s, %s)"
            val = (filename,data,objects)
            c.execute(sql,val)
            conn.commit()
            c.close()
            conn.close()
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed searching data in MySQL table {}".format(error))
            
    def updateImage(data,filename):
        try:
            c,conn = connection()
            sql = "UPDATE images SET newphoto = %s WHERE imagename = %s"
            val = (data, filename)
            c.execute(sql, val)
            conn.commit()
            c.close()
            conn.close()
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed searching data in MySQL table {}".format(error))
    #insert into objects table all objects' properties of an image
    def insertObjects(imagename,objectname,score,x,y,width,height):
        try:
            c,conn = connection()
            sql = "INSERT INTO objects (imagename,class_name,score,x,y,width,height) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            val = (imagename,objectname,score,x,y,width,height)
            c.execute(sql, val)
            conn.commit()
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed inserting data into MySQL table {}".format(error))
        finally:
            c.close()
            conn.close()
    def retrievePhoto(imagename):
        try:
            c,conn = connection()
            sql = "SELECT photo from images where imagename = %s"
            val=(imagename,)
            c.execute(sql, val)
            record = c.fetchone()
            if(c.rowcount>0):
                c.close()
                conn.close()
                return record
            else:
                return 0
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed searching data int MySQL table {}".format(error))
            
    def retrievePhotoDetection(imagename):
        try:
            c,conn = connection()
            sql = "SELECT newphoto from images where imagename = %s"
            val=(imagename,)
            c.execute(sql, val)
            record = c.fetchone()
            if(c.rowcount>0):
                c.close()
                conn.close()
                return record
            else:
                return 0
        except mysql.connector.Error as error :
            conn.rollback()
            print("Failed searching data int MySQL table {}".format(error))
            
    def searchImageNameFromObject(name):
        try:
            c,conn = connection()
            sql = "SELECT imagename from objects WHERE class_name = %s"
            val = (name,)
            c.execute(sql,val)
            record = c.fetchall()
            if(c.rowcount>0):
                c.close()
                conn.close()
                return record
            else:
                return 0
        except mysql.connector.Error as error:
            conn.rollback()
            print("Failed searching data int MySQL table {}".format(error))
        

        
        
        