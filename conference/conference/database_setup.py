import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DATETIME, DATE, TIME, func, types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy import create_engine
 
from datetime import date, time 

Base = declarative_base()

class Person():
    __tablename__ = 'person'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    phone = Column(String(20))
    email = Column(String(250))
    address = Column(String(100))
    picture = Column(String(250))
    
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
           'phone'        : self.phone,
           'email'        : self.email,
           'address'      : self.address,
           'picture'      : self.picture,
       }    

class NameSerialize():
    @property
    def name_serialize(self):
       return self.name

class AppUser(Base, Person, NameSerialize):
    __tablename__ = 'appuser'

    sessions = relationship(
        'Session',
        secondary='wishlist'
    )

class Speaker(Base, Person, NameSerialize):
    __tablename__ = 'speaker'

class Conference(Base, NameSerialize):
    __tablename__ = 'conference'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    date = Column(DATE, default=func.current_timestamp())
     
    owner_id = Column(Integer,ForeignKey('appuser.id'))
    owner = relationship(AppUser, backref=backref('owner', uselist=False)) 
    
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
           'date'         : str(self.date),
           'owner_id'     : self.owner_id,
       }
 
class TypeOfSession(Base, NameSerialize):
    __tablename__ = 'typeofsession'

    id = Column(Integer, primary_key = True)
    name = Column(String(30), nullable = False)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
       }

class Location(Base, NameSerialize):
    __tablename__ = 'location'

    id = Column(Integer, primary_key = True)
    name = Column(String(250), nullable = False)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
       }

class Session(Base, NameSerialize):
    __tablename__ = 'appsession'

    id = Column(Integer, primary_key = True)
    name = Column(String(250), nullable = False)

    date = Column(DATE, default=func.current_timestamp())
    time = Column(TIME, default=func.current_timestamp())
    documents = Column(String(150))
    
    duration = Column(String(20))
    highlights = Column(String(250))

    conference_id = Column(Integer,ForeignKey('conference.id'))
    conference = relationship(Conference, backref=backref('appsession', uselist=False))

    type_of_session_id = Column(Integer,ForeignKey('typeofsession.id'))
    type_of_session = relationship(TypeOfSession, backref=backref('appsession', uselist=False))

    speaker_id = Column(Integer,ForeignKey('speaker.id'))
    speaker = relationship(Speaker, backref=backref('appsession', uselist=False))

    location_id = Column(Integer,ForeignKey('location.id'))
    location = relationship(Location, backref=backref('appsession', uselist=False))
    room = Column(String(10))
    
    users = relationship(
        'AppUser',
        secondary='wishlist'
    )    

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'                 : self.id,
           'name'               : self.name,
           'date_time'          : str(self.date_time),
           'duration'           : self.duration,
           'highlights'         : self.highlights,
           'conference_id'      : self.conference_id,
           'type_of_session_id' : self.type_of_session_id,
           'speaker_id'         : self.speaker_id,
           'location_id'        : self.location_id,
           'documents'          : self.documents           
        }

class Img(Base):
    __tablename__ = "img"
    
    id = Column(Integer, primary_key=True)
    image = Column(types.LargeBinary)
    filetype = Column(String(10))
    filename = Column(String(50))
    session_id = Column(Integer,ForeignKey('appsession.id'))
    session = relationship(Session, backref=backref('appsession', uselist=True))
    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'                 : self.id,
           'session_id'         : self.session_id,
           'filename'           : self.filename,
           'filetype'           : self.filetype
       }
  
class WishList(Base):
    __tablename__ = 'wishlist'
    user_id = Column(Integer, ForeignKey('appuser.id'), primary_key=True)
    session_id = Column(Integer, ForeignKey('appsession.id'), primary_key=True)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'user_id'           : self.user_id,
           'session_id'         : self.session_id,
       }

class Register(Base):
    __tablename__ = 'register'
    user_id = Column(Integer, ForeignKey('appuser.id'), primary_key=True)
    conference_id = Column(Integer, ForeignKey('conference.id'), primary_key=True)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'user_id'           : self.user_id,
           'conference_id'     : self.conference_id,
       }

engine = create_engine('postgresql://conference:dbpassword@localhost/conference', echo=False)
Base.metadata.create_all(engine)
