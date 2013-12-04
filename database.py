from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.types import DECIMAL
from utils import calculate_score, timeformat
from config import DBCHOICE, USERNAME, PASSWORD, DBHOST, DBPORT, DBNAME

import os
import time
#Base class for OMR table
_Base = declarative_base()

class Singleton(object):
 
    '''
 
    Singelton class
 
    '''
 
    def __init__(self, decorated):
 
        self._decorated = decorated
 
    def instance(self, *args, **kwargs):
 
        try:
 
            return self._instance
 
        except AttributeError:
 
            self._instance = self._decorated(*args, **kwargs)
 
            return self._instance
 
    def __call__(self, *args, **kwargs):
 
        raise TypeError('Singletons must be accessed through the `Instance` method.')

@Singleton
class ServiceDB():
  
    def __init__(self, sqlite_path='/home/catsky/Desktop/workspace/phoenix-flower/data/db/'):
        
        # Valid SQLite URL forms are:
        # sqlite:///:memory: (or, sqlite://)
        # sqlite:///relative/path/to/file.db
        # sqlite:///C:\\path\\to\\database.db
        if DBCHOICE == "sqlite":
            print "DBCHOICE =sqlite"
            if sqlite_path is not None:
                if not os.path.exists(sqlite_path):
                    os.makedirs(sqlite_path)
                self.dbconn_str = "sqlite:///%s%s" % (
                                           sqlite_path,
                                           "sqlite.data")
            else:
                print "Error! need db path to create sqlite schema"
                raise

            print "db path: " + self.dbconn_str
        elif DBCHOICE == "mysql":
            print "DBCHOICE =mysql"
            self.dbconn_str = "mysql+mysqldb://%s:%s@%s:%s/%s"%(
                                                USERNAME,
                                                PASSWORD,
                                                DBHOST,
                                                DBPORT,
                                                DBNAME)
#         elif DBCHOICE == "postgresql":
#             print "DBCHOICE =postgresql"
#                 ServiceDB.dbconn_str = "postgresql://%s:%s@localhost:%s/%s" % (
#                                                cfg.getUSERNAME(),
#                                                cfg.getPASSWORD(),
#                                                cfg.getDBPORT(),
#                                                cfg.getDBNAME())
#                 ServiceDB.engine = create_engine(ServiceDB.dbconn_str,
#                                                  pool_size=10,
#                                                  pool_recycle=3600)
        else:
            raise
        self.engine = create_engine(self.dbconn_str)
        self.Session = sessionmaker(bind=self.engine)
        _Base.metadata.create_all(self.engine)
        self.session = self.Session()
    
    def instance(self):
        pass
     
    def saveMoneyMinute(self, tuple_in):
        try:
            moneyminutes = Money_Minute(name=tuple_in[0], timestamp=tuple_in[1], value=tuple_in[2])
            self.session.add(moneyminutes)
            self.session.commit()
        except:
            self.session.rollback()
        finally:
            self.session.close()
    
    def queryMoneyMinutes(self, count=30):
        #return latest cur of last 30 minutes
        query = self.session.query(Money_Minute).order_by(Money_Minute.id.desc()).limit(count).all()
        print len(query)
        for index, row in enumerate(query):
            row.timeshow = timeformat(row.timestamp)
            if index % 3 == 0:
                row.annotation = str(row.value)
            else:
                row.annotation = ''
            print '>>%s'%row.id
        query.reverse()
        
        return query
    
    def saveMoneyHour(self, tuple_in):
        try:
            moneyhours = Money_Hour(name=tuple_in[0], timestamp=tuple_in[1], value=tuple_in[2])
            self.session.add(moneyhours)
            self.session.commit()
        except:
            self.session.rollback()
        finally:
            self.session.close()
        
    def queryMoneyHours(self, count=None):
        query = self.session.query(Money_Hour).order_by(Money_Hour.id.desc()).all()
        for index, row in enumerate(query):
            row.timeshow = timeformat(row.timestamp)
            if index % 3 == 0:
                row.annotation = str(row.value)
            else:
                row.annotation = ''
        if count != None:
            query = query[:count]
        query.reverse()
        return query
    
    def queryArticlesByHot(self, count=32, offset=0):
        query = self.session.query(Article).all()
        now = time.time()
        for row in query:
            if self.isFaved(article_id=row.id, user_id=row.user_id):
                row.faved = True
            else:
                row.faved = False
            delta_hours = int((now-row.timestamp)/3600)
            hot = calculate_score(row.score, delta_hours)
            row.hot = hot
        query = sorted(query, reverse=True)       
        
        for index, row in enumerate(query):
            row.rowid = index + 1
        if len(query) > offset:
            query = query[offset-1:(count+offset+1)]
        else:
            query = query[:count]
        return query
    
    def queryArticlesByLatest(self, count=32, offset=0):
        query = self.session.query(Article).order_by(Article.timestamp.desc()).all()
        for row in query:
            if self.isFaved(article_id=row.id, user_id=row.user_id):
                row.faved = True
            else:
                row.faved = False
        
        for index, row in enumerate(query):
            row.rowid = index + 1
        if len(query) > offset:
            query = query[offset-1:(count+offset+1)]
        else:
            query = query[:count]
        return query
    
    def isFaved(self, article_id, user_id):
        exist = self.session.query(Favorite).filter_by(user_id=user_id, article_id=article_id).count()
        if exist > 0:
            return True
        else:
            return False
        
        
    def saveFav(self, **data):
        timestamp = time.time()
        article_id = data['article_id']
        user_id = data['user_id']
        try:
            fav = Favorite(timestamp = timestamp, article_id = article_id, user_id = user_id)
            self.session.add(fav)        
            self.session.flush()
            fav.article.score += 1
            self.session.commit()
        except:
            self.session.rollback()
        finally:
            self.session.close()   

    def addUser(self, **data):
        try:
            user = User(name=data['name'], email=data['email'], password=data['password'])
            self.session.add(user)
            self.session.commit()
        except:
            self.session.rollback()
        finally:
            self.session.close()
    
class Money_Minute(_Base):
    __tablename__ = 'money_minutes'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    timestamp = Column(DECIMAL, nullable=False)
    value = Column(Float, nullable=False)
        
    def __repr__(self):
        print "<Money_Minute (%s, %s, %s)>" % (self.id, self.timestamp, self.value)
        
class Money_Hour(_Base):
    __tablename__ = 'money_hours'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    timestamp = Column(DECIMAL, nullable=False)
    value = Column(Float, nullable=False)

    def __repr__(self):
        print "<Money_Hour (%s, %s, %s)>" % (self.id, self.timestamp, self.value)

class User(_Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
       
    def __repr__(self):
        print "<User (%s, %s, %s)>" % (self.name, self.email, self.password)
    
        
class Article(_Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    URL = Column(String(200), nullable=False, unique=True)
    score = Column(Integer, default=0)
    hot = Column(Float, default=0.0)
    timestamp = Column(Float, nullable=False)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", backref=backref('articles', order_by=id))
    
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    category = relationship("Category", backref=backref('articles', order_by=id))
    
    def __cmp__(self, other):
        if self.hot > other.hot:
            return 1
        else:
            return -1
   
    def __repr__(self):
        print "<Article (%s)>" % (self.title)
        
class Category(_Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
        
    def __repr__(self):
        print "<Category (%s)>" % (self.name)
        
        
class Favorite(_Base):
    __tablename__ = 'favorites'
    id = Column(Integer, primary_key=True)
    timestamp = Column(Float, nullable=False)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", backref=backref('favorites', order_by=id))
    
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    article = relationship("Article", backref=backref('favorites', order_by=id))
    
    def __repr__(self):
        print "<Favorite (%s, %s)>" % (self.user.name, self.article.title)
     
if __name__ == '__main__':
    db = ServiceDB.instance()
    import time
    q=db.queryMoneyMinutes()
    for i in q:
        print i.id
#     query = db.queryArticles(30)
#     for row in query:
#         print row.title
#         print type(row.user)
#         if row.user is not None:
#             print row.user
    #add user
#     ken = dict(name='ken', email='zhdh@gmc.om', password='pass')
#     db.addUser(**ken)
    #add article
#     import random
#     rstr = str(random.randint(0,100000))
#     
#     cat = Category(name='life'+rstr)
#     
#     db.session.add(cat)
#     db.session.flush()
#     art = Article(title="title", URL="http://www.baidu.com/q="+rstr, 
#                   user_id=1, category_id=cat.id,
#                   timestamp=time.time())
#     db.session.add(art)
#     db.session.flush()
#     #fav = Favorite(timestamp=time.time(), user_id=ken.id, article_id=art.id)
#     data = dict(timestamp=time.time(), user_id=ken.id, article_id=art.id)
#     db.saveFav(**data)
#     db.session.close()
    import sys
    sys.exit()
#     for row in db.queryMoneyMinutes():
#         print "%s %s %s %s %s" % (row.name, row.timestamp, row.value, row.timeshow, row.annotation)
#     for row in db.queryMoneyHours():
#         print "%s %s %s %s %s" % (row.name, row.timestamp, row.value, row.timeshow, row.annotation)