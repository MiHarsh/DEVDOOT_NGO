from flask import Flask, render_template, request, flash, redirect, url_for, session, logging
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_mail import Mail, Message
from random import randint , randrange
import requests
import time
import datetime
import pyrebase
import hashlib
import json

from facebook import GraphAPI
from threading import Thread
import tweepy

##import os
##from PIL import Image
##import numpy as np
##import cv2


def read_creds(filename):
    with open(filename) as f:
        credentials = json.load(f)
    return credentials
 
credentials = read_creds('credentials.json')


config = credentials['firebase_config']

firebase = pyrebase.initialize_app(config)
db = firebase.database() 

################################################################  Send Tweet and FB Post

graph = GraphAPI(access_token=credentials['fb']['access_token'])

try:
    oauth = tweepy.OAuthHandler(credentials['twitter']['consumer_key'],credentials['twitter']['consumer_secret_key'])
    oauth.set_access_token(credentials['twitter']['access_token'],credentials['twitter']['access_token_secret'])
except Exception as e:
    oauth = None

twitter_api = tweepy.API(oauth)

def post_fb(message):
    '''
    There can be multiple groups(pages where we can send)
    '''
    groups = ['105244575107030']

    try: 
        for group in groups:
            graph.put_object(group,'feed', message=message)
        return True
    except:
        return False 

def post_tweet(message):
    try:
        twitter_api.update_status(message)
        return True
    except:
        return False


################################################################

app = Flask(__name__)
admin_number=credentials['admin_number']['admin_number']

############################################### SEND MAIL IN BACKGROUND THREAD

app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = credentials['admin_mail']['admin_mail']
app.config['MAIL_PASSWORD'] = credentials['admin_password']['admin_password']
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


def send_async_email(app,msg):
    with app.app_context():
        mail.send(msg)

def send_email(msg):
       thr = Thread(target=send_async_email,args=[app,msg])
       thr.start()
       return thr

###############################################


class signupForm(Form):
    country_code = StringField('Country Code', [
        validators.DataRequired(),
        validators.Length(min=3, max=3)],default= '+91') 
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

class forgotmob(Form):
    mob_num = StringField('Mobile Number', [
        validators.DataRequired(),
        validators.Length(min=10, max=10)
    ])

class forgotpass(Form):
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


# Check if the user is admin
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
        country_code = form.country_code.data

        users = db.child("Users").get().val()
        for x in users:
            if users[x]['mob_num'] == mob_num:
                flash("An account with this number already exists", "danger")
                return redirect(url_for('signup'))
        
        
        

        name = form.name.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()
        today = datetime.datetime.now()
        t_date = today.strftime("%d") + "/" + today.strftime("%m") + "/" + today.strftime("%Y")
        p_time = today.strftime("%H") + ":" + today.strftime("%M") + ":" + today.strftime("%S")

        data = {
            "country_code": country_code,
            "name": name,
            "mob_num": mob_num,
            "password": password,
            "date_account_created":t_date,
            "time_account_created":p_time,
            "is_account_active":1,
            "raised_requests":""
        }

        session["verify_user_details"] = data
        
        number = data["mob_num"]
        session["mob_num"] = number
        session["is_login_signup"] = True  # To reuse the resend endpoint
        session["country_code"] = country_code
        status,otp_temp,time_otp = getOTPApi(country_code,number)
        session['current_otp']   = str(otp_temp)
        session['current_time']  = time_otp

        if status:
            return redirect(url_for("verifyOTP"))

        flash('Something went wrong', 'danger')
        return redirect(url_for("signup"))

    else:
        this_User=""
        this_User_num=""
        if 'logged_in' in session: 
            this_User =session['username']
            this_User_num=session['mob_num']
        return render_template("signup.html" ,form = form , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)


################################################################  Verify OTP

def getOTPApi(country_code,number):
    session['wrong_otp_count'] = 0 # to give attempts

    otp_temp = randrange(100000,999999)
    URL = f"http://2factor.in/API/V1/132183a5-bd1d-11eb-8089-0200cd936042/SMS/{country_code+number}/{otp_temp}" 
    r = requests.get(url = URL).json()
    
    t0 = time.time()
    if r["Status"] == "Success":
        return (True,otp_temp,t0)
    else:
        return (False,otp_temp,t0)


@app.route('/verifyOTP',methods=['GET','POST'])
def verifyOTP():
    
    if request.method == 'POST':

        r_otp = request.form['otp']
        t1 = time.time()
        wrong_otp_count = session['wrong_otp_count']

        if((t1 - session.get('current_time')) < 150):
            if( session.get('current_otp') == r_otp):
                data = session.get("verify_user_details")
                db.child("Users").push(data)
                session["current_time"] = -1
                flash('you are now registered and can log in', 'success')
                return redirect(url_for("login"))
            else:
                wrong_otp_count+=1
                session['wrong_otp_count'] = wrong_otp_count #update in session too
                if wrong_otp_count < 3:
                    flash(f'wrong otp, you have { 3 - wrong_otp_count } chances left !!', 'danger')
                    return redirect(url_for("verifyOTP"))
                else:
                    flash(f'You have exhausted your chances,try again !!', 'danger')
                    return redirect(url_for("signup"))

        flash('otp was expired, please resend OTP', 'danger')
        return redirect(url_for("verifyOTP"))
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("verify.html" , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)

################################################################  Resend OTP

@app.route('/resendOTP')
def resendOTP():

    number = session["mob_num"]
    country_code = session["country_code"]
    status,otp_temp,time_otp = getOTPApi(country_code,number)
    session['current_otp']   = str(otp_temp)
    session['current_time']  = time_otp

    if status:
        if session["is_login_signup"]:
            return redirect(url_for("verifyOTP"))
        return redirect(url_for("forgot_verify_otp"))

    flash('Something went wrong', 'danger')
    if session["is_login_signup"]:
        return redirect(url_for("signup"))
    return redirect(url_for("forgot"))



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
            session['country_code'] = user['country_code']
            session['user_id'] = user_id
            session['is_admin']  = False
            if mob_num == admin_number:
                session['is_admin']  = True
            flash('Welcome ' + user['name'] + '!', 'success')
            print(session)
            return redirect(url_for('index'))

    else:
        this_User=""
        this_User_num=""
        if 'logged_in' in session: 
            this_User =session['username']
            this_User_num=session['mob_num']
        return render_template("login.html" ,form = form , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)


################################################################  Forgot - Enter Mob

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    form = forgotmob(request.form)
    session["is_login_signup"] = False  # To reuse the resend endpoint
    if request.method == 'POST' and form.validate():
        mob_num = form.mob_num.data

        users = db.child("Users").get().val()
        user = None
        user_id = None

        for x in users:
            if users[x]['mob_num'] == mob_num :
                user = users[x]
                user_id = x
                print(user)
                break

        if user is None:
            app.logger.info("Udd gye tote in forgot mode")
            flash('Please check your credentials', 'danger')
            return redirect(url_for('forgot'))

        else:
            app.logger.info("Welcome")

            session['username'] = user['name']
            session['mob_num'] = user['mob_num']
            session['user_id'] = user_id
            session['country_code'] = user['country_code']
            flash('Welcome ' + user['name'] + '!', 'success')
            print(session)
            country_code = session['country_code']
            status,otp_temp,time_otp = getOTPApi(country_code,mob_num)
            session['current_otp']   = str(otp_temp)
            session['current_time']  = time_otp

            if status:
                return redirect(url_for("forgot_verify_otp"))

            flash('Something went wrong', 'danger')
            return redirect(url_for("forgot"))

    else:
        this_User=""
        this_User_num=""
        if 'logged_in' in session: 
            this_User =session['username']
            this_User_num=session['mob_num']
        return render_template("forgot_mob.html" ,form = form , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)


################################################################  Forgot - Enter OTP

@app.route('/forgot_verify_otp', methods=['GET','POST'])
def forgot_verify_otp():
    if request.method == 'POST':
        r_otp = request.form["forgot_otp"]
        t1 = time.time()
        wrong_otp_count = session['wrong_otp_count']
        if((t1 - session.get('current_time')) < 150):
            if( session.get('current_otp') == r_otp):
                session["current_time"] = -1
                flash('You can now enter your new password', 'success')
                return redirect(url_for("update_password"))
            else:
                wrong_otp_count+=1
                session['wrong_otp_count'] = wrong_otp_count #update in session too
                if wrong_otp_count < 3:
                    flash(f'wrong otp, you have { 3 - wrong_otp_count } chances left !!', 'danger')
                    return redirect(url_for("forgot_verify_otp"))
                else:
                    flash(f'You have exhausted your chances !!', 'danger')
                    return redirect(url_for("forgot"))

        flash('otp was expired, please resend OTP', 'danger')
        return redirect(url_for("forgot_verify_otp")) 
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("forgot_verify_otp.html" , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)



################################################################  Forgot - Update Password

@app.route('/update_password', methods=['GET','POST'])
def update_password():
    form = forgotpass(request.form)
    if request.method == 'POST' and form.validate():
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        user_id = session['user_id']

        usr_ref = db.child("Users").child(user_id)
        usr_ref.update({
            'password':password
        })

        flash('you have successfully changed password and can log in', 'success')
        return redirect(url_for("login"))
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("forgot_change_pass.html",form = form , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)



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
        pin = f_data['pin']
        Profession = f_data['Profession']

        Volunteers = db.child("Volunteers").get().val()

        for x in Volunteers:
            if Volunteers[x]['mob_num'] == mob_num:
                flash('Volunteers with this Number allready exist', 'danger')
                return redirect(url_for("index"))
        
        '''mob_per = "0"
        email_per = "0"
 
        if (f_data['mob_per']).upper() == "YES":  
            mob_per="1"
        if (f_data['email_per']).upper() == "YES":  
            email_per="1"
        '''
        today = datetime.datetime.now()
        t_date = today.strftime("%d") + "/" + today.strftime("%m") + "/" + today.strftime("%Y")
        p_time = today.strftime("%H") + ":" + today.strftime("%M") + ":" + today.strftime("%S")

        data = {
            "name": name,
            "mob_num": mob_num,
            "email": email,
            "city": city,
            "date":t_date,
            "pin_code":pin,
            "Profession": Profession
        }
        print("hiii")
        db.child("Volunteers").push(data)

        flash('you are now a Volunteers and can help other', 'success')

        return redirect(url_for("index"))
    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("be_vol.html" , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)

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
        pin = f_data['pin']
        data = {
            "city": city,
            "issue": issue,
            "issue_subject":issue_subject,
            "date": t_date,
            "status":0,
            "pin_code":pin,
            "is_archive":0
        }
        admin_mail="devdootsena@gmail.com"
        msg = Message(str(issue_subject) + " - " + str(city), sender="devdootsena@gmail.com", recipients=[admin_mail])
        msg.body = str(issue +'\r\n \r\n'+"By :- "+str(session['username'])+" \r\n ("+str(session['mob_num'])+")\r\n City :- "+str(city) )
        send_email(msg) # send mail in background thread


        message = f"Subject : {issue_subject}\n\n Issue : {issue}\n\n City : {city}\n Contact : {session['mob_num']}"

        flag1 = post_fb(message)
        flag2 = post_tweet(message)

        db.child("Users/"+session['user_id']+"/raised_requests").push(data)

        if(flag1 & flag2):
            flash('you Issue has been raised', 'success')
            return redirect(url_for("index"))
        
        flash('Something went wrong', 'danger')
        this_User=""
        this_User_num=""
        if 'logged_in' in session: 
            this_User =session['username']
            this_User_num=session['mob_num']
        return render_template("raise_request.html" , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)

    this_User=""
    this_User_num=""
    if 'logged_in' in session: 
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("raise_request.html" , this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)

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
    db.child("Users/" + session['user_id']+"/raised_requests/"+req_id).update({
            'status':1
        })
    flash('Congratulations ,Hope your are  safe!!', 'success')
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

#########################################  ALL pending RAISED ISSUE

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

#########################################  ALL solved RAISED ISSUE

@app.route('/solved_raised_issue')
@is_admin
def solved_raised_issue():
    this_User=""
    this_User_num=""
    if 'logged_in' in session:
        this_User =session['username']
        this_User_num=session['mob_num']
    users = db.child("Users").get().val()
    return render_template("solved_raised_issue.html", this_User=this_User , users=users ,this_User_num=this_User_num ,admin_number=admin_number)

####################################### Remove Volunteer

@app.route("/remove_volunteer" + "/<req_id>", methods=['POST'])
@is_admin
def remove_volunteer(req_id):
    name = db.child("Volunteers/" +req_id+ "/name").get().val()
    db.child("Volunteers/" +req_id).remove()
    flash(name+ 'has been removed from Volunteers', 'success')
    return redirect(url_for('volunteer_list'))


####################################################################################### adding Blog by admin

@app.route('/add_blog' , methods=['GET','POST'] )
@is_admin
def add_blog():
    if request.method == 'POST':
        f_data = request.form
        author = f_data['author']
        title = f_data['title']
        para1=f_data['para1']
        today = datetime.datetime.now()
        t_date = today.strftime("%d") + "/" + today.strftime("%m") + "/" + today.strftime("%Y")
        p_time = today.strftime("%H") + ":" + today.strftime("%M") + ":" + today.strftime("%S")
        data = {
            "author": author,
            "time":p_time,
            "date":t_date,
            "title": title,
            "para1":para1,
            "user_id":session['user_id']
        }
        db.child("blogs").push(data)
        flash('Your Blog has been Shared', 'success')
        return redirect(url_for('blogs'))
    this_User=""
    this_User_num=""
    if 'logged_in' in session:
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("add_blog.html", this_User=this_User , this_User_num=this_User_num ,admin_number=admin_number)
    
################################################################################################ delete blog


@app.route("/delete_blog" + "/<blog_id>", methods=['POST'])
@is_admin
def delete_blog(blog_id):
    db.child("blogs/"+blog_id).remove()
    flash('Blog Deleted', 'success')
    return redirect(url_for('blogs'))

############################################################################################## Blogs view page

@app.route("/blogs")
def blogs():
    blogs = db.child("blogs").get().val()
    this_User=""
    this_User_num=""
    if 'logged_in' in session:
        this_User =session['username']
        this_User_num=session['mob_num']
    return render_template("blogs.html", this_User=this_User , blogs=blogs , this_User_num=this_User_num ,admin_number=admin_number)


###################################################################################Archive my raised issue


@app.route("/archive_raised_request" + "/<id>", methods=['POST'])
@is_logged_in
def archive_raised_request(id):
    db.child("Users/" + session['user_id']+"/raised_requests/"+id).update({
            'is_archive':1
        })
    flash('successfully Archived', 'success')
    return redirect(url_for('my_raised_request'))

###########################################################################Privacy page

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

#######################################################################################################

if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
