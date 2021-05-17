from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_mail import Mail, Message
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



mail = Mail(app)
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "div143har@gmail.com"
app.config['MAIL_PASSWORD'] = 'Div@143@Har'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
admin_number="8239335509"





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
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("index.html", this_User = this_User , this_User_num=this_User_num ,admin_number=admin_number)




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


###################################################################################################


# Check if the currentuser is admin
def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session['is_admin']:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized', 'danger')
            return redirect(url_for('index'))

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
            "password": password,
            "raised_requests":""
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
            if mob_num == admin_number:
                session['is_admin']  = True
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

        Volunteers = db.child("Volunteers").get().val()

        for x in Volunteers:
            if Volunteers[x]['mob_num'] == mob_num:
                flash('Volunteers with this Number allready exist', 'danger')
                return redirect(url_for("index"))

        mob_per = "0"
        email_per = "0"
 
        if (f_data['mob_per']).upper() == "YES":  
            mob_per="1"
        if (f_data['email_per']).upper() == "YES":  
            email_per="1"

        data = {
            "name": name,
            "mob_num": mob_num,
            "email": email,
            "city": city,
            "Profession": Profession,
            "mob_per" : mob_per,
            "email_per":email_per
        }
        print("hiii")
        db.child("Volunteers").push(data)

        flash('you are now a Volunteers and can help other', 'success')

        return redirect(url_for("index"))

    return render_template("be_vol.html")

################################################################################################# Rasing Request

@app.route('/raise_request', methods=['GET','POST'])
@is_logged_in
def raise_request():
    if request.method == 'POST':
        f_data = request.form
        issue = f_data['issue']
        city = f_data['city']
        issue_subject=f_data['issue_subject']
        today = datetime.datetime.now()
        t_date = today.strftime("%d") + "/" + today.strftime("%m") + "/" + today.strftime("%Y")
        p_time = today.strftime("%H") + ":" + today.strftime("%M") + ":" + today.strftime("%S")

        data = {
            "city": city,
            "issue": issue,
            "issue_subject":issue_subject,
            "date": t_date
        }
        admin_mail="div143har@gmail.com"
        msg = Message(str(issue_subject) + " - " + str(city), sender='div143har@gmail.com', recipients=[admin_mail])
        msg.body = str(issue +'\r\n \r\n'+"By :- "+str(session['username'])+" \r\n ("+str(session['mob_num'])+")\r\n City :- "+str(city) )
        mail.send(msg)

        db.child("Users/"+session['user_id']+"/raised_requests").push(data)

        flash('you Issue has been raised', 'success')

        return redirect(url_for("index"))

    return render_template("raise_request.html")

####################################################################################### My raised request

@app.route('/my_raised_request')
@is_logged_in
def my_raised_request():
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    issues = db.child("Users/"+session['user_id']+"/raised_requests").get().val()
    return render_template("my_raised_request.html", this_User = this_User  , this_User_num=this_User_num, admin_number=admin_number ,issues=issues)


####################################################################################### Delet my raised request

@app.route("/delete_raised_request" + "/<req_id>", methods=['POST'])
def delete_raised_request(req_id):
    print(req_id)
    db.child("Users/" + session['user_id']+"/raised_requests/"+req_id).remove()
    flash('Raised Request Deleted', 'success')
    return redirect(url_for('my_raised_request'))



######################################################################################### volunteer list

@app.route('/volunteer_list')

def volunteer_list():
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    v_info = db.child("Volunteers").get().val()
    return render_template("volunteer_list.html", this_User = this_User , session = session ,v_info=v_info ,this_User_num=this_User_num,admin_number=admin_number )




########################################################################################## Doctor complete

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for("index"))

####################################################  Only for  admin

#########################################  ALL RAISED ISSUE

@app.route('/pending_raised_issue')
@is_admin
def pending_raised_issue():
    this_User=""
    this_User_num=""
    if 'logged_in' in session:
        this_User =session['username']
        this_User_num=session['mob_num']
    users = db.child("Users").get().val()
    return render_template("pending_raised_issue.html", this_User=this_User , users=users ,this_User_num=this_User_num ,admin_number=admin_number)

####################################### Remove Volunteer

@app.route("/remove_volunteer" + "/<req_id>", methods=['POST'])
@is_admin
def remove_volunteer(req_id):
    name = db.child("Volunteers/" +req_id+ "/name").get().val()
    db.child("Volunteers/" +req_id).remove()
    flash(name+ 'has been removed from Volunteers', 'success')
    return redirect(url_for('volunteer_list'))


#######################################################################################################

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
