"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import g
from flask import render_template
from flask import request
from flask import url_for

import json
import logging

import sys

# Date handling 
import arrow   
from dateutil import tz  # For interpreting local times

# Mongo database
import pymongo
from pymongo import MongoClient

import config
CONFIG = config.configuration()


MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)


print("Using URL '{}'".format(MONGO_CLIENT_URL))


###
# Globals
###

app = flask.Flask(__name__)
app.secret_key = CONFIG.SECRET_KEY

####
# Database connection per server process
###

try: 
    dbclient = MongoClient(MONGO_CLIENT_URL)
    db = getattr(dbclient, CONFIG.DB)
    collection = db.memos

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)



###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  g.memos = get_memos()
  for memo in g.memos: 
      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')


# We don't have an interface for creating memos yet
@app.route("/add")
def create():
    app.logger.debug("Create Memo")
    return flask.render_template('add.html')


@app.route("/_add_memo")
def add_memo():
    app.logger.debug("Add Memo")
    memo_date = arrow.get(request.args.get('memo_date')).isoformat()
    memo_text = request.args.get('memo_text')
    record = {"type": "dated_memo",
              "date": memo_date,
              "text": memo_text
             }
    collection.insert(record)
    return flask.jsonify()


@app.route("/_del_memo")
def del_memo():
    app.logger.debug("Delete Memo")
    memo_date = arrow.get(request.args.get('memo_date')).isoformat()
    memo_text = request.args.get('memo_text')
    memo_text = memo_text.replace('<br>', '\n')
    record = collection.find_one({"type": "dated_memo", "date": memo_date, "text": memo_text})
    if record:
        collection.remove(record)
    return flask.jsonify()


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################


@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """
    try:
        then = arrow.get(date).to('local')
        now = arrow.now()
        now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if then.date() == now.date():
            human = "Today"
        else: 
            human = then.humanize(now)
            if human == "in a day":
                human = "Tomorrow"
            if human == "a day ago":
                human = "Yesterday"
    except: 
        human = date
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    sort_memos()
    records = [ ]
    for record in collection.find( { "type": "dated_memo" } ):
        record['date'] = arrow.get(record['date']).isoformat()
        record['text'] = record['text'].replace('\n', '<br>')
        del record['_id']
        records.append(record)
    return records 

def sort_memos():
    for doc in collection.find( { "type": "dated_memo" } ).sort("date", pymongo.ASCENDING):
        collection.remove(doc)
        collection.insert(doc)

if __name__ == "__main__":
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    app.run(port=CONFIG.PORT,host="0.0.0.0")

    
