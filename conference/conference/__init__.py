from flask import Flask, render_template, request, redirect, jsonify, url_for, send_from_directory
from flask import session as login_session
from flask import Response, make_response


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oauth2client.client import Credentials, flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
import requests
from functools import wraps

from xml.etree import ElementTree
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement

import random
import string
import os
import shutil

from database_setup import Base, AppUser, Speaker, Conference, Session, WishList,\
    TypeOfSession, Location, Register, Img
import db_CRUD
from db_CRUD import app, csrf, APP_ROOT, UPLOAD_FOLDER, DOWNLOAD_FOLDER


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        user_id = login_session.get("user_id")
        if user_id is None:
            return redirect(url_for('showLogin', next=request.url))

        return f(*args, **kwargs)
    return decorated_function

CLIENT_ID = json.loads(
    open(os.path.join(APP_ROOT, 'client_secrets.json'), 'r').read())['web']['client_id']

APPLICATION_NAME = "Project3"

#--------------------------------------------------------------------------------------
# Only for Project 1
@app.route('/project1')
def showproject1():
    return render_template('project1.html')
#--------------------------------------------------------------------------------------

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(
            string.ascii_uppercase +
            string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    # Exchange client token for long-lived server-side token
    # GET
    # /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret=
    # {app-secret}&fb_exchange_token={short-lived-token}
    app_id = json.loads(open(os.path.join(APP_ROOT, 'fb_client_secrets.json'), 'r').read())['web']['app_id']
    app_secret = json.loads(open(os.path.join(APP_ROOT, 'fb_client_secrets.json'), 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s'% (
          app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.3/me"
    # strip expire tag from access token
    token = result.split("&")[0]
    
    url = 'https://graph.facebook.com/v2.3/me?%s' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # Get user picture
    url = 'https://graph.facebook.com/v2.3/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = db_CRUD.getUserID(login_session['email'])
    if not user_id:
        user_id = db_CRUD.createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;\
              -webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    return output    

@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():

    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(os.path.join(APP_ROOT, 'client_secrets.json'), scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token

    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['provider'] = 'google'
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    response = make_response(json.dumps('Successfully connected user.', 200))

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user = db_CRUD.getUser(login_session['email'])
    if not user:
        user = db_CRUD.createUser(login_session)

    login_session['user_id'] = user.id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px; \
                -webkit-border-radius: 150px; -moz-border-radius: 150px;"> '
    return output

# DISCONNECT - Revoke a current user's token and reset their login_session

@app.route('/gdisconnect')
def gdisconnect():

    # Only disconnect a connected user.
    user_id = login_session.get('user_id')
    if user_id is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = login_session['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
            #del login_session['credentials']

        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
    return redirect(url_for('showConferences'))

@app.route('/')
def showWelcome():
    """ Show welcome page."""
    user_id = login_session.get("user_id")
    user_name = login_session.get("username")
    return render_template('welcome.html',
                           user_id=user_id,
                           user_name=user_name)

@app.route('/conference')
def showConferences():
    """ Show all conferences and the latest sessions."""

    conferences = db_CRUD.getConferences()
    sessions = db_CRUD.get_latest_sessions()
    user_id = login_session.get("user_id")
    user_name = login_session.get("username")

    return render_template('conferences.html',
                           conferences=conferences,
                           sessions=sessions,
                           user_id=user_id,
                           user_name=user_name)

@app.route('/conference/registered/', methods=['GET', 'POST'])
def showRegisteredConferences():
    """ Show the registered conferences of a user and their sessions."""

    user_id = login_session.get("user_id")
    user_name = login_session.get("username")
    conferences = db_CRUD.getConferences(user_id, "registered")
    sessions = db_CRUD.getSessionsOfConferences(conferences)
    if request.method == 'POST':
        if db_CRUD.unregister(request.form, user_id) == True:
            return render_template('inform.html',
                                   task="Unregister Conference",
                                   info='Some conference(s) have been unregistered successfully.',
                                   url='showRegisteredConferences')
        else:
            return render_template('inform.html',
                                   task="Unregister Conference",
                                   info="You didn't select any conference to unregister.",
                                   url='showRegisteredConferences')
    else:
        return render_template('registeredconferences.html',
                               conferences=conferences,
                               sessions=sessions,
                               user_id=user_id,
                               user_name=user_name)

@app.route('/conference/created/')
def showCreatedConferences():
    """ Show the conferences which a user created and their sessions."""

    user_id = login_session.get("user_id")
    user_name = login_session.get("username")
    conferences = db_CRUD.getConferences(user_id, "owner")
    sessions = db_CRUD.getSessionsOfConferences(conferences)

    return render_template('createdconferences.html',
                           conferences=conferences,
                           sessions=sessions,
                           user_id=user_id,
                           user_name=user_name)

@app.route('/conference/addConference/', methods=['GET', 'POST'])
@login_required
def addConference():
    """ Create a new conference."""

    user_login_id = login_session.get("user_id")

    if request.method == 'POST':
        db_CRUD.addConference(request.form, user_login_id)
        return render_template('inform.html',
                               task="Create a new conference",
                               info="Conference %s is successfully created." % request.form['name'],
                               url='showConferences', conference_id=0)
    else:
        return render_template('addconference.html')


@app.route('/conference/<int:conference_id>/deleteconference/',
           methods=['GET', 'POST'])
@login_required
def deleteConference(conference_id):
    """ Delete a conference."""

    user_login_id = login_session.get("user_id")

    conference = db_CRUD.getConferenceByID(conference_id)
    if not conference:
        return render_template('inform.html', task="Delete a conference",
                               info="The conference with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    owner = (user_login_id == conference.owner_id)
    if not owner:
        return render_template('inform.html', task="Delete a conference",
                               info="You must be the owner of the conference to be authorized to this task.",
                               url='showConferences', conference_id=0)

    if request.method == 'POST':
        db_CRUD.deleteConference(conference.id)
        return render_template('inform.html', task="Delete a conference",
                               info="Conference %s has been successfully deleted." % conference.name,
                               url='showConferences', conference_id=0)
    else:
        return render_template('deleteconference.html', conference=conference)


@app.route('/conference/<int:conference_id>/modifyconference/',
           methods=['GET', 'POST'])
@login_required
def modifyConference(conference_id):
    """ Modify a conference."""

    user_login_id = login_session.get("user_id")

    conference = db_CRUD.getConferenceByID(conference_id)
    if not conference:
        return render_template('inform.html', task="Modify a conference",
                               info="The conference with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    is_owner = (user_login_id == conference.owner_id)
    if not is_owner:
        return render_template('inform.html', task="Modify a conference",
                               info="You must be the owner of the conference to be authorized to this task.",
                               url='showConferences', conference_id=0)

    if request.method == 'POST':
        db_CRUD.modifyConference(request.form, conference.id)
        return render_template('inform.html', task="Modify a conference",
                               info='Conference %s has been successfully modified' % request.form['name'],
                               url='showSessions',
                               conference_id=conference.id)
    else:
        return render_template('modifyconference.html', conference=conference)


@app.route('/conference/conference_register/', methods=['GET', 'POST'])
@login_required
def conferenceRegister():
    """ Allow user to register to the conferences."""

    user_id = login_session.get("user_id")
    user_name = login_session.get("username")

    conferences = db_CRUD.getConferences()

    if request.method == 'POST':
        if db_CRUD.conferenceRegister(request.form, user_id) == True:
            return render_template('inform.html',
                                   task="Conference Register",
                                   info='Your register is successful.',
                                   url='showRegisteredConferences')
        else:
            return render_template('inform.html',
                                   task="Conference Register",
                                   info='You did not select any conference.',
                                   url='showConferences', conference_id=0)
    else:
        return render_template('conferenceregister.html',
                               conferences=conferences, 
                               user_id=user_id,
                               user_name=user_name)


@app.route('/conference/<int:conference_id>/showsessions/',
           methods=['GET', 'POST'])
def showSessions(conference_id):
    """ Show all sessions of a conference.
        Allow user to mark his or her favorite sessions.
        Allow the conference's organizer to modify or delete the conference and its sessions."""

    conferences = db_CRUD.getConferences()
    conference = db_CRUD.getConferenceByID(conference_id)

    if not conference:
        return render_template('inform.html', task="Modify a conference",
                               info="The conference with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    sessions = db_CRUD.getSessionsOfConference(conference_id)

    user_id = login_session.get("user_id")
    user_name = login_session.get("username")

    is_owner = (user_id == conference.owner_id)
    if request.method == 'POST':
        if db_CRUD.addToWishList(request.form, user_id) == True:
            return render_template('inform.html',
                                   task="Update Wishlist",
                                   info='Some new session(s) have been added to your wishlist.',
                                   url='showWishList', user_id=user_id)
        else:
            return render_template('inform.html',
                                   task="Update Wishlist",
                                   info='You did not select any session.',
                                   url='showSessions', conference_id=conference_id)
    else:
        return render_template('showsessions.html',
                               conferences=conferences,
                               conference=conference,
                               sessions=sessions,
                               user_id=user_id,
                               is_owner=is_owner,
                               user_name=user_name)
        # is_owner==True: the user is allowed to modify, delete the conference,
        # and add, modify, delete its sessions.


@app.route('/conference/<int:user_id>/showwishlist/', methods=['GET', 'POST'])
def showWishList(user_id):
    """ Show the Wishlist for a user, allow him or her to remove (unmark) some sessions."""

    sessions = db_CRUD.getSessionsFromWishList(user_id)
    user = db_CRUD.getUserInfo(user_id)

    user_name = user.name if user else None

    if request.method == 'POST':
        if db_CRUD.removeFromWishList(request.form, user_id) == True:
            return render_template('inform.html',
                                   task="Update Wishlist",
                                   info='Some session(s) have been removed from your wishlist.',
                                   url='showWishList', user_id=user_id)
        else:
            return render_template('inform.html',
                                   task="Update Wishlist",
                                   info="You didn't select any session to remove.",
                                   url='showWishList', user_id=user_id)

    else:
        return render_template('showwishlist.html', user_id=user_id, user_name=user_name,
                               sessions=sessions)


@app.route('/conference/<session_id>/modifysession/', methods=['GET', 'POST'])
@login_required
def modifySession(session_id):
    """ Allow the owner of the conference to modify his or her session,
        and add/remove its documents."""

    user_login_id = login_session.get("user_id")

    session = db_CRUD.getSessionByID(session_id)
    if not session:
        return render_template('inform.html',
                               task="Modify a session",
                               info="The session with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    conference = db_CRUD.getConferenceBySessionID(session_id)

    is_owner = (user_login_id == conference.owner_id)
    if not is_owner:
        return render_template('inform.html',
                               task="Modify a session",
                               info="You must be the owner of the conference to be authorized \
                                     to this task.",
                               url='showSessions', conference_id=conference.id)

    if request.method == 'POST':
        if db_CRUD.modifySession(request.form, request.files, session_id):
            return render_template('inform.html',
                                   task="Modify a session",
                                   info="Session %s has been modified successfully." %request.form['name'],
                                   url='showSessions', conference_id=conference.id)
        else:
            return render_template('inform.html',
                                   task="Modify a session",
                                   info="Failed to modify: the number of the documents is too big or \
                                         the name of some documents is too long.",
                                   url='showSessions', conference_id=conference.id)

    else:
        filenames = db_CRUD.getFilename(session_id)

        return render_template('modifysession.html',
                               conference=conference,
                               session=session,
                               day=str(session.date),
                               start_time=str(session.time),
                               filenames=filenames)


@app.route('/conference/<int:session_id>/deletesession/',
           methods=['GET', 'POST'])
@login_required
def deleteSession(session_id):
    """ Allow the owner of the conference to delete a session."""

    user_login_id = login_session.get("user_id")

    session = db_CRUD.getSessionByID(session_id)
    if not session:
        return render_template('inform.html',
                               task="Delete a session",
                               info="The session with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    conference = db_CRUD.getConferenceBySessionID(session_id)
    is_owner = (user_login_id == conference.owner_id)
    if not is_owner:
        return render_template('inform.html',
                               task="Delete a session",
                               info="You must be the owner of the conference to be authorized to this task.",
                               url='showConferences', conference_id=0)

    if request.method == 'POST':
        db_CRUD.deleteSession(session_id)
        return redirect(
            url_for('showSessions', conference_id=session.conference_id))
    else:
        return render_template('deletesession.html', session=session)

@app.route('/download/<filename>/')
def downloadFile(filename):
    """ Download filename."""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

def downloadFiles(filenames):
    """ Download the documents that user have chosen."""

    shutil.rmtree(app.config['DOWNLOAD_FOLDER'], ignore_errors=True)

    for filename in filenames:
        shutil.copy(os.path.join(app.config['UPLOAD_FOLDER'],filename), app.config['DOWNLOAD_FOLDER'])

    archive_name = os.path.expanduser(os.path.join(app.config['DOWNLOAD_FOLDER'], 'documents'))
    root_dir = os.path.expanduser(app.config['DOWNLOAD_FOLDER'])

    shutil.make_archive(archive_name, 'gztar', root_dir)

    return redirect(url_for('downloadFile', filename='documents.tar.gz'))
 
@app.route('/conference/<int:conference_id>/<int:session_id>/showdocument/',
           methods=['GET', 'POST'])
def showDocument(conference_id, session_id):
    """ Show the images and the documents of a session, allow user to download the documents."""

    image_filenames = db_CRUD.showImage(session_id)
    session_name = db_CRUD.getSessionByID(session_id).name
    document_filenames = db_CRUD.getDocumentFilename(session_id)
    if not(document_filenames and document_filenames != []) \
            and not(image_filenames and image_filenames != []):
        return render_template('inform.html',
                               task="Session Documents",
                               info="There is not any document for this session.",
                               url='showSessions', conference_id=conference_id)
    else:
        if request.method == 'POST':
            download_filenames = request.form.getlist('check')
            if download_filenames == []:
                return render_template('inform.html',
                                       task="Download Documents",
                                       info="You did not select any document.",
                                       url='showSessions', conference_id=conference_id)
            else:
                return downloadFiles(download_filenames)
                
        else:
            return render_template('showdocument.html',
                                   conference_id=conference_id,
                                   session_id=session_id,
                                   session_name=session_name,
                                   document_filenames=document_filenames,
                                   image_filenames=image_filenames)


@app.route('/conference/<int:conference_id>/addsession/',
           methods=['GET', 'POST'])
@login_required
def addSession(conference_id):
    """ Allow the owner of the conference to add a new session and upload its documents."""

    conference = db_CRUD.getConferenceByID(conference_id)
    if not conference:
        return render_template('inform.html',
                               task="Add a session",
                               info="The conference with that id doesn't exist.",
                               url='showConferences', conference_id=0)

    user_login_id = login_session.get("user_id")

    is_owner = (user_login_id == conference.owner_id)
    if not is_owner:
        return render_template('inform.html',
                               task="Add a session",
                               info="You must be the owner of the conference to be authorized \
                                     to this task.",
                               url='showSessions', conference_id=conference_id)

    if request.method == 'POST':
        if db_CRUD.addSession(request.form, request.files, conference_id):
            return render_template('inform.html',
                                   task="Add a session",
                                   info="Session %s has been added successfully." %request.form['name'],
                                   url='showSessions', conference_id=conference_id)
        else:    
            return render_template('inform.html',
                                   task="Add a session",
                                   info="Documents added Failed: the number of the documents is too big \
                                         or the name of some documents is too long. Please try again.",
                                   url='showSessions', conference_id=conference_id)
    else:
        return render_template('addsession.html', conference=conference)

# JSON APIs to view information of all sessions in a conference
@app.route('/conference/<int:conference_id>/sessions/JSON')
def conferenceSessionsJSON(conference_id):
    sessions = db_CRUD.getSessionsOfConference(conference_id)
    return jsonify(sessions=[i.serialize for i in sessions])

# JSON APIs to view information of a session
@app.route('/conference/session/<int:session_id>/JSON')
def sessionJSON(session_id):
    session = db_CRUD.getSessionByID(session_id)
    if session:
        return jsonify(session=session.serialize)

# JSON APIs to view information of all conferences
@app.route('/conference/JSON')
def conferencesJSON():
    conferences = db_CRUD.getConferences()
    return jsonify(conferences=[r.serialize for r in conferences])

# JSON APIs to view information of all sessions
@app.route('/sessions/JSON')
def sessionsJSON():
    sessions = db_CRUD.getSessionsOfConference()
    return jsonify(sessions=[r.serialize for r in sessions])

# JSON APIs to view information of all users
@app.route('/users/JSON')
def usersJSON():
    usernames = db_CRUD.getUserInfo()
    return jsonify(users=[r.serialize for r in usernames])

# JSON APIs to view information of all speakers
@app.route('/speakers/JSON')
def speakersJSON():
    speakers = db_CRUD.getSpeakers()
    return jsonify(Speakers=[r.serialize for r in speakers])

# JSON APIs to view information of all wishlists
@app.route('/wishlist/JSON')
def wishlistJSON():
    wishlists = db_CRUD.getWishList()
    return jsonify(wishlists=[r.serialize for r in wishlists])

# JSON APIs to view information of all wishlists
@app.route('/register/JSON')
def registerJSON():
    registers = db_CRUD.getRegister()
    return jsonify(registers=[r.serialize for r in registers])

# JSON APIs to view information of all images
@app.route('/image/JSON')
def imageJSON():
    images = db_CRUD.getImageInfo()
    return jsonify(images=[r.serialize for r in images])

# JSON APIs to view information of all speakers
@app.route('/name/JSON')
def nameJSON():
    return db_CRUD.getName()

# XML APIs to view information of all conferences
def xml_creator():
    top = Element('top')
    conferences = db_CRUD.getConferences()
    for conf in conferences:
        conference = SubElement(top, 'conference')
        SubElement(conference, 'conf', id=str(conf.id))
        SubElement(conference, 'conf', name=conf.name)
        SubElement(conference, 'conf', date=str(conf.date))

        sessions = db_CRUD.getSessionsOfConference(conf.id)
        for sess in sessions:
            session = SubElement(conference, 'session')
            SubElement( session, 'sess', id=str(sess.id))
            SubElement( session, 'sess', name=sess.name)
            SubElement( session, 'sess', date=str(sess.date))
            SubElement( session, 'sess', time=str(sess.time))
            SubElement( session, 'sess', duration=sess.duration)
            SubElement( session, 'sess', highlights=sess.highlights)
            SubElement( session, 'sess', type_of_session=sess.type_of_session.name)
            SubElement( session, 'sess', location=sess.location.name)
            SubElement( session, 'sess', speaker=sess.speaker.name)

    return prettify(top)

def prettify(elem):
    """ Return a pretty-printed XML string for the Element.
    copied from: http://pymotw.com/2/xml/etree/ElementTree/create.html
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

@app.route('/conference.xml')
def conference_xml():
    """ Returns all of the conferences and their associated sessions in XML form."""
    return Response(xml_creator(), mimetype='application/xml')


if __name__ == '__main__':

    db_CRUD.makeDirectories()
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
