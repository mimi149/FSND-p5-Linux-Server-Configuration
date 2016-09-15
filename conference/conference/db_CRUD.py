from flask import Flask, jsonify, send_from_directory
from flask.ext.seasurf import SeaSurf

import json

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, asc, desc, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, AppUser, Speaker, Conference, Session, WishList
from database_setup import TypeOfSession, Location, Register, Img
from werkzeug import secure_filename
import datetime, os
import sqlite3
import imghdr
import urllib

IMAGE_SHOW_FOLDER = 'static/upload_images'
UPLOAD_FOLDER = 'static/upload_folder'
DOWNLOAD_FOLDER = 'static/download_folder'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
csrf = SeaSurf(app)

app.config['IMAGE_SHOW_FOLDER'] = os.path.join(APP_ROOT, IMAGE_SHOW_FOLDER)
app.config['UPLOAD_FOLDER'] = os.path.join(APP_ROOT, UPLOAD_FOLDER)
app.config['DOWNLOAD_FOLDER'] = os.path.join(APP_ROOT, DOWNLOAD_FOLDER) 

engine = create_engine('postgresql://conference:dbpassword@localhost/conference')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
s = DBSession()

def makeDirectories():
    """ Make necessary directories if not exists"""
    
    folders = [IMAGE_SHOW_FOLDER, UPLOAD_FOLDER, DOWNLOAD_FOLDER]
    for folder in folders:
        try: 
            os.makedirs(folder)
        except OSError:
            if not os.path.isdir(folder):
                raise 
    return
   
def getName():
    """ Make a file static/names.json to store the names of speakers, locations, type_of_sections
        to use in the input form for users not to retype the existent names."""
        
    speakers = s.query(Speaker).all()
    locations = s.query(Location).all()
    type_of_sessions = s.query(TypeOfSession).all()

    json_name = jsonify(speaker=[r.name_serialize for r in speakers],
                        location=[r.name_serialize for r in locations],
                        type_of_session=[r.name_serialize for r in type_of_sessions])

    name_dictionary = {}
    
    name_dictionary["speaker"] = [r.name_serialize for r in speakers]
    name_dictionary["location"] = [r.name_serialize for r in locations]
    name_dictionary["type_of_session"] = [r.name_serialize for r in type_of_sessions]

    filename = open(os.path.join(APP_ROOT, 'static/names.json'), 'w')
    json.dump(name_dictionary, filename)
    filename.close()
    return json_name
    
def init_db(dbname):
    engine = create_engine(dbname, echo=False)
    s.remove()
    s.configure(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    return engine

# User Helper Functions
def createUser(login_session):
    newUser = AppUser(name = login_session['username'], 
                      email = login_session['email'], 
                      picture = login_session['picture'])
    s.add(newUser)
    s.commit()
    user = s.query(AppUser).filter_by(email = login_session['email']).first()
    return user

def getUserInfo(user_id=0):
    """ Get info of a user with the given user_id, otherwise get info of all users."""
    
    if user_id == 0:
        return s.query(AppUser).all()
    else:
        return s.query(AppUser).filter_by(id = user_id).first()

def getUserID(email):
    try:
        user = s.query(AppUser).filter_by(email = email).first()
        return user.id
    except:
        return None

def getUser(email):
    try:
        user = s.query(AppUser).filter_by(email = email).first()
        return user
    except:
        return None
def getImageInfo():
    return s.query(Img).all()
    
def date_convert(date): 
    """ Convert the Unicode date type from the html form to a date object of Python."""
    
    date = str(date)
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    return date

def time_convert(time): 
    """ Convert the Unicode time type from the html form to a time object of Python."""
    
    time = str(time)+":00" if len(str(time)) < 8 else str(time)
    time = datetime.datetime.strptime(time, "%H:%M:%S").time()
    return time

def getOwner(session_id):
    try:
        session = s.query(Session).filter_by(id = session_id).first()
        owner_id = session.conference.owner__id
        return owner_id
    except:
        return None

def addConference(form, owner_id):
    conference = Conference(name = form['name'], date = date_convert(form['date']), owner_id = owner_id)
    s.add(conference)
    s.commit()
    print "\n conference.name: ", conference.name

def deleteConference(conference_id):
    """ Solve foreign keys in sessions and Registers."""
    
    #Delete all the sessions belonging to this conference.
    deleteSessions(conference_id)

    # Delete all the registers that users have with this conference.
    deleteRegisters(conference_id)
    
    conference = getConferenceByID(conference_id)
    if conference:
        s.delete(conference)
        s.commit()

def modifyConference(form, conference_id):
    conference = getConferenceByID(conference_id)    
    if conference:
        conference.name = form['name']
        conference.date = date_convert(form['date'])
        s.add(conference)
        s.commit()

def getConferences(userID=0, filterBy=None):
    """ Return all conferences."""
    try:
        if userID and (filterBy == "registered"):
            return s.query(Conference).join(Register).filter(Register.user_id==
                                                             userID).order_by(asc(Conference.name)).all()
        elif userID and (filterBy == "owner"):
            return s.query(Conference).filter(Conference.owner_id==
                                              userID).order_by(asc(Conference.name)).all()
        else:
            return s.query(Conference).order_by(asc(Conference.name)).all()

    except:
        return []

def getConferenceBySessionID(session_id):
    """ Given a session id, return the conference including that session."""
    
    session = getSessionByID(session_id)
    if session:
        return session.conference
    else:
        return None

def getConferenceByID(conference_id):
    """ Given a conference id, return that conference."""
    
    try:
        return s.query(Conference).filter_by(id=conference_id).first()
    except:
        return None

def getSessionByID(session_id):
    """ Given a session id, return that session."""
    
    try:
        return s.query(Session).filter_by(id=session_id).first()
    except:
        return None

def getSessionsOfConference(conference_id=0):
    """ Given a conference_id, return a list of all sessions of that conference, 
        otherwise return a list of all sessions of all conferences."""
        
    if conference_id == 0:
        return s.query(Session).order_by(Session.date, Session.time).all()
    else:
        return s.query(Session).filter_by(conference_id=conference_id).\
               order_by(Session.date, Session.time).all()

def getSessionsOfConferences(conferences):
    """ Return all sessions of a list of conferences."""

    sessions = []
    for conference in conferences:
        sessions.extend(getSessionsOfConference(conference.id))
    return sessions

def getSessionsInAConferenceByType(conference_id, type_of_session_id):
    """ Given a conference, return all sessions of a specific type and belong to that conference,
        otherwise return an empty list."""
        
    return s.query(Session).filter_by(conference_id=conference_id,
                                       type_of_session_id=type_of_session_id).all()
    
def getSessionsBySpeaker(speaker_id):
    """ Given a speaker, return a list of all sessions given by this particular speaker, 
        across all conferences, otherwise return an empty list."""
        
    return s.query(Session).filter_by(speaker_id=speaker_id).all()

def addTypeOfSession(type_of_session_name):
    """ Add a new type of session.
        This function is called only from the function getTypeOfSessionID."""
        
    type_of_session = TypeOfSession(name = type_of_session_name)
    s.add(type_of_session)
    s.commit()

    getName() # update the file of all the names of speakers, locations, type of sessions
    
    type_of_session = s.query(TypeOfSession).filter_by(name=type_of_session_name).first()
    return type_of_session.id  
  
def getTypeOfSessionID(type_of_session_name):
    type_of_session = s.query(TypeOfSession).filter_by(name=type_of_session_name).first()
    if not type_of_session:
        return addTypeOfSession(type_of_session_name)
    return type_of_session.id
    
def addSpeaker(speaker_name):
    """ Add a new speaker.
        This function is called only from the function getSpeakerID."""
        
    speaker = Speaker(name = speaker_name)
    s.add(speaker)
    s.commit()

    getName() # update the file of all the names of speakers, locations, type of sessions
    
    speaker = s.query(Speaker).filter_by(name=speaker_name).one()
    return speaker.id  
  
def getSpeakerID(speaker_name):
    speaker = s.query(Speaker).filter_by(name=speaker_name).first()
    if not speaker:
        return addSpeaker(speaker_name)
    return speaker.id

def getSpeakers():
    """ Get info of all speakers."""
    
    return s.query(Speaker).all()

def addLocation(location_name):
    """ Add a new location
        This function is called from the function getLocationID."""

    location = Location(name = location_name)
    s.add(location)
    s.commit()
    
    getName() # update the file of all the names of speakers, locations, type of sessions
    
    location = s.query(Location).filter_by(name=location_name).one()
    return location.id  
  
def getLocationID(location_name):
    location = s.query(Location).filter_by(name=location_name).first()
    if not location:
        return addLocation(location_name)
    return location.id

def insert_image(image_file, session_id):
    """ Insert content of files into database."""
    
    with open(os.path.join(app.config['UPLOAD_FOLDER'],image_file), 'rb') as input_file:
        ablob = input_file.read()
        base = os.path.basename(image_file)
        afile, ext = os.path.splitext(base)
        sql = '''insert into img (image, filetype, filename, session_id)
                values(:ablob, :ext, :afile, :id);'''
        param = {'ablob':sqlite3.Binary(ablob), 'ext':ext, 'afile':afile, 'id':session_id}
        s.execute(sql,param) 
        s.commit()

def saveFile(files, session_id):
    """ Upload document files for a session to the server,
        Insert the images into database,
        Delete the uploaded image files.
        The documents other than images are stored in the folder static/upload_folder
        This function return a string of document names to be stored in database later."""
    
    document_list = []
    upload_files = files.getlist('file[]',None)
    for file in upload_files:
        filename = secure_filename(file.filename)
        if filename != '':
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            image_type = imghdr.what(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            if not image_type:
                document_list.append(filename + ",")
            else:
                insert_image(filename, session_id)
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'],filename))

    document_name_str = ''.join(document_list)
    return document_name_str

def extractImage(session_id):
    """ Extract the images from the database and write to files.
     Return the list of names of the new written files."""
     
    filenames = []
    sql = "select image, filetype, filename from img where session_id = :id"
    param = {'id': session_id}
    images = s.execute(sql, param).fetchall()
    for image in images:
        ablob, ext, afile = image
        filename = afile + ext

        with open(os.path.join(app.config['IMAGE_SHOW_FOLDER'], filename), 'wb') as output_file:
            output_file.write(ablob)
            output_file.close()

        filenames.append("/" + os.path.join(IMAGE_SHOW_FOLDER, filename))
    return filenames

def getFilename(session_id):
    """ Get the list of image files and other document files of a session."""
    
    image_list = []
    images = s.query(Img).filter_by(session_id=session_id).all()   
    for image in images:
        filename = image.filename + image.filetype
        image_list.append(filename)
        
    session = s.query(Session).filter_by(id=session_id).first()
    document_list = session.documents.split(",") if session.documents else []
    if document_list != []:
        document_list.pop() # remove the last empty string.   
    filenames = list(set(document_list).union(set(image_list)))
    return filenames

def showImage(session_id):
    """ Call extractImage to extract images from database to the folder static/upload_images.
        Return a list of image filenames."""

    image_filenames = extractImage(session_id)
    return image_filenames

def getDocumentFilename(session_id):
    """ Return a list of document filenames."""

    session = s.query(Session).filter_by(id=session_id).first()
    if session and session.documents:
        document_filenames = session.documents.split(",")
        document_filenames.pop() # remove the last empty string.   
        return document_filenames
    else:
        return None
        
def addSession(form, files, conference_id):
    """ Open only to the owner of the conference.
        Add a new session."""
    
    type_of_session_id = getTypeOfSessionID(form["type_of_session"])
    speaker_id = getSpeakerID(form["speaker"])
    location_id = getLocationID(form["location"])
    
    session = Session(name = form["name"],
                      date = date_convert(form["date"]),
                      time = time_convert(form["start_time"]),
                      duration = form["duration"],
                      highlights = form["highlights"],
                      conference_id = conference_id,
                      type_of_session_id = type_of_session_id,
                      speaker_id = speaker_id,
                      location_id = location_id,
                      room = form["room"])
    s.add(session)
    s.commit()
    session = s.query(Session).filter_by(name =  form["name"], conference_id = conference_id).first()

    # Call saveFile to upload documents. The images will be stored in database, other documents
    # will be keeped in a folder and their names will be stored in database.
    document_name_str = saveFile(files, session.id)
    if len(document_name_str) < 150:
        session.documents = document_name_str
        s.add(session)
        s.commit()
        return True
    else: 
        return False

def modifySession(form, files, session_id):
    """ Open only to the owner of the conference
        Modify a session."""

    session = getSessionByID(session_id)    
   
    if session:
        type_of_session_id = getTypeOfSessionID(form["type_of_session"])
        speaker_id = getSpeakerID(form["speaker"])
        location_id = getLocationID(form["location"])
        session.name = form['name']
        session.date = date_convert(form["date"]),
        session.time = time_convert(form["start_time"]),
        session.duration = form['duration']
        session.highlights = form['highlights']
        session.type_of_session_id = type_of_session_id
        session.speaker_id = speaker_id
        session.location_id = location_id
        session.room = form['room']

        # Call saveFile to upload new documents. The images will be stored in database, other documents
        # will be keeped in a folder and their names will be stored in database.
        document_name_str = saveFile(files, session.id)
        
        if session.documents == None:
            session.documents = ""
        
        if len(session.documents) + len(document_name_str) < 150:
            if session.documents:
                session.documents += document_name_str
            else:
                session.documents = document_name_str
            s.add(session)
            s.commit()

            removeDocument(form, session_id)
            return True
        else:
            return False    

def deleteSessions(conference_id):
    for session in s.query(Session).filter_by(conference_id=conference_id).all():
        deleteSession(session.id)
    s.commit()

def deleteRegisters(conference_id):
    """ Delete all the registers to a conference.
        Should email to all users who made these registers."""
    
    for register in s.query(Register).filter_by(conference_id=conference_id).all():
        s.delete(register)
    s.commit()

def removeDocument(form, session_id):
    """ The form contains the document filenames which the owner of the session wants to remove.
        This function deletes all those documents from the database."""

    filenames = form.getlist('check')   
    remove_document_list = []
    for filename in filenames:
        remove_document_list.append(filename)

        if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'],filename)):
            # Process the documents other than images.
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'],filename))

        else: 
            # Process the images
            base = os.path.basename(filename)
            afile, ext = os.path.splitext(base)
            document = s.query(Img).filter_by(filetype=ext, filename=afile, session_id=session_id).first()
            if document:
                s.delete(document)
                s.commit()
    if remove_document_list != []: 
        # Update session.documents
        session = s.query(Session).filter_by(id=session_id).first()
        current_document_list = session.documents.split(",")
        current_document_list.pop() # remove the last empty string.   
        new_document_list = list(set(current_document_list) - set(remove_document_list ))
        
        new_list = []
        for item in new_document_list:
            new_list.append(item+",") 
        
        new_document_name_str = ''.join(new_list)
        session.documents = new_document_name_str
        s.add(session)
        s.commit()

      
def deleteDocument(session_id):
    """ Delete all the documents related to a session from the database.
        This function is called from deleteSession."""

    for document in s.query(Img).filter_by(session_id=session_id).all():
        s.delete(document)
    s.commit()        

def deleteSessionFromWishList(session_id, user_id):
    """ Unmark the session which this user marked before."""
    
    try:
        wishlist = s.query(WishList).filter_by(session_id=session_id, user_id=user_id).one()
        s.delete(wishlist)
        s.commit()
    except:
        return None

def deleteConferenceFromRegister(conference_id, user_id):
    """ Unregister for this conference."""

    try:
        conference = s.query(Register).filter_by(conference_id=conference_id, user_id=user_id).one()
        s.delete(conference)
        s.commit()
    except:
        return None

def getSessionsFromWishList(user_id):
    """ Get all the marked sessions for a user."""
    
    return s.query(Session).join(WishList).filter(WishList.user_id==user_id).\
           order_by(Session.date, Session.time).all() 

def deleteWishListsWithSessionID(session_id):    
    """ Delete all the marks to a session.
        Should EMAIL to all the users who marked this session in their wishlists."""

    for wishlist in s.query(WishList).filter_by(session_id=session_id).all():
        s.delete(wishlist)
    s.commit()

def deleteWishListsWithUserID(user_id):
    """ Delete all the marks to all sessions in a user's wishlist.
        Should EMAIL to the user who possesses these wishlists."""

    for wishlist in s.query(WishList).filter_by(user_id=user_id).all():
        s.delete(wishlist)
    s.commit()

def deleteSession(session_id):
    """ Solve foreign key in WishList:
        Delete all the wishlists that users have with this session.
        Delete all the documents of this session."""

    deleteWishListsWithSessionID(session_id)
    deleteDocument(session_id)
    session = getSessionByID(session_id)
    if session:
        s.delete(session)
        s.commit()
      
def addSessionToWishlist(user_id, session_id):
    """ When a user marks a session, add the session to his or her wishList,
        This function is called from addToWishList."""
    
    wishlist = s.query(WishList).filter_by(user_id=user_id, session_id=session_id).first()
    if not wishlist:
        wishlist = WishList(user_id = user_id, session_id = session_id)
        s.add(wishlist)
        s.commit()

def addToWishList(form, user_id):
    """ The form contains the checkboxes which indicate the sessions the user
        wants to add to his or her wishlist."""
    
    session_id_list = form.getlist('check')
    for session_id in session_id_list:
        addSessionToWishlist(user_id, int(session_id))
    return len(session_id_list) > 0 # Some new wishlist has been added.

def removeFromWishList(form, user_id):
    """ The form contains the checkboxes which indicate the sessions the user
        wants to remove from his or her wishlist."""

    session_id_list = form.getlist('check')   
    for session_id in session_id_list:
        deleteSessionFromWishList(int(session_id), user_id)
    return len(session_id_list) > 0 # Some wishlist has been removed.

def unregister(form, user_id):
    """ The form contains the checkboxes which indicate the conferences the user
        wants to unregister."""

    conference_id_list = form.getlist('check')   
    for conference_id in conference_id_list:
        deleteConferenceFromRegister(int(conference_id), user_id)
    return len(conference_id_list) > 0 # Some conferences have been removed.

def getWishList():
    return s.query(WishList).all()
   
def getRegister():
    return s.query(Register).all()

def get_latest_sessions(numberOfRows=10):
    """ Get latest sessions."""

    count = s.query(func.count(Session.id)).scalar()
    offset = count - numberOfRows if count > numberOfRows else 0
    return s.query(Session).order_by(Session.date, Session.time).slice(offset, count)

def conferenceRegister(form, user_id):
    """ The form contains the checkboxes which indicate the conferences the user
     wants to register to attend."""
    
    conference_id_list = form.getlist('check')  
    for conference_id in conference_id_list:
        addConferenceToRegister(user_id, int(conference_id))
    return len(conference_id_list) > 0 # Some conferences have been registered.
 
def addConferenceToRegister(user_id, conference_id):  
    """ When a user register a conference, add an instance to Register if it doesn't exist.
     This function is called from conferenceRegister()."""
    
    register = s.query(Register).filter_by(user_id=user_id, conference_id=conference_id).first()
    if not register:
        register = Register(user_id = user_id, conference_id=conference_id)
        s.add(register)
        s.commit()
    
def getMarkedSessionsInAConference(conference_id):
    """ Query for all the marked sessions in a conference."""
    
    return session.query(Session).join(WishList).filter_by(Session.conference_id==conference_id).all() 
