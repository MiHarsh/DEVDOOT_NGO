from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
##from flask_mail import Mail, Message
from random import randint
import requests
import time
import datetime
import pyrebase
import hashlib
##import os
##from PIL import Image
##import numpy as np
##import cv2


config = {
    "apiKey": "AIzaSyDYIcnYja88Q85jSzWezTKlSWAfhJWnJs8",
    "authDomain": "devdoot-c612a.firebaseapp.com",
    "databaseURL": "https://devdoot-c612a-default-rtdb.firebaseio.com",
    "projectId": "devdoot-c612a",
    "storageBucket": "devdoot-c612a.appspot.com",
    "messagingSenderId": "479627305477",
    "appId": "1:479627305477:web:58f7d13d77aa09e049726c",
    "measurementId": "G-SCR49DP51V"
  }

firebase = pyrebase.initialize_app(config)
db = firebase.database() 

app = Flask(__name__)

'''
for mail

mail = Mail(app)
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "swarajxxx69@gmail.com"
app.config['MAIL_PASSWORD'] = 'swarajfucks'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

'''



class signupForm(Form):
    mob_num = StringField('Mobile Number', [
        validators.DataRequired(),
        validators.Length(min=10, max=10)
    ])
    name = StringField('Name', [validators.Length(min=1, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirmed', message='Passwords do not match')
    ])
    confirmed = PasswordField('Confirm Password')


class loginForm(Form):
    mob_num = StringField('Mobile Number', [
        validators.DataRequired(),
        validators.Length(min=10, max=10)
    ])
    password = PasswordField('Password', [
        validators.DataRequired()
    ])

############################################################# index

@app.route('/')
def index():
    print(session)
    this_User=""
    if 'logged_in' in session: 
        this_User =session['username']
    return render_template("index.html", this_User = this_User)




###################################################################################################

# Check if the user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


################################################################  User Signup

@app.route('/signup' , methods=['GET', 'POST'])
def signup():
    form =signupForm(request.form)
    if request.method == 'POST'and form.validate():
        mob_num = form.mob_num.data
        print(mob_num)

        users = db.child("Users").get().val()
        for x in users:
            if users[x]['mob_num'] == mob_num:
                flash("An account with this number already exists", "danger")
                return redirect(url_for('signup'))
        

        name = form.name.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        data = {
            "name": name,
            "mob_num": mob_num,
            "password": password
        }
        db.child("Users").push(data)

        flash('you are now registered and can log in', 'success')

        return redirect(url_for("login"))
    else:
        return render_template("signup.html" ,form = form)




################################################################  User Login

@app.route('/login', methods=['GET','POST'])
def login():
    form = loginForm(request.form)
    if request.method == 'POST' and form.validate():
        mob_num = form.mob_num.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        users = db.child("Users").get().val()
        user = None
        user_id = None

        for x in users:
            if users[x]['mob_num'] == mob_num and users[x]['password'] == password:
                user = users[x]
                user_id = x
                print(user)
                break

        if user is None:
            app.logger.info("Udd gye tote")
            flash('Please check your credentials', 'danger')
            return redirect(url_for('login'))

        else:
            app.logger.info("Welcome")

            session['logged_in'] = True
            session['username'] = user['name']
            session['mob_num'] = user['mob_num']
            session['user_id'] = user_id
            session['is_admin']  = False
            flash('Welcome ' + user['name'] + '!', 'success')
            print(session)
            return redirect(url_for('index'))

    else:
        return render_template("login.html" ,form = form)


#################################################################################################

@app.route('/become_volunteer', methods=['GET','POST'])
@is_logged_in
def become_volunteer():
    if request.method == 'POST':
        f_data = request.form
        name = session['username']
        mob_num = session['mob_num']
        email = f_data['email']
        city = f_data['city']
        Profession = f_data['Profession']
        mob_per = f_data['mob_per']
        email_per = f_data['email_per']

        data = {
            "name": name,
            "mob_num": mob_num,
            "email": email,
            "city": city,
            "Profession": Profession,
            "mob_per" : mob_per,
            "email_per":email_per
        }

        db.child("Volunteers").push(data)

        flash('you are now a Volunteers and can help other', 'success')

        return redirect(url_for("index"))

    return render_template("be_vol.html")



########################################################################################## Doctor complete

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for("index"))



#######################################################################################################

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
