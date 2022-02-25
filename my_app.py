# import flask dependencies
from flask import Flask, request, make_response, jsonify, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from socket import gethostname
from datetime import datetime


# initialize the flask app
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://simoh:password@simoh.mysql.pythonanywhere-services.com/simoh$timetable"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

migrate = Migrate()
migrate.init_app(app, db)

#Database models

class Study_class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable = False)
    year_of_study = db.Column(db.Integer)
    timetable = db.relationship('Timetable', backref='class_lookup', lazy=True)

class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    timetable = db.relationship('Timetable', backref='day_lookup', lazy=True)

class Lecturer(db.Model):
    PF_no = db.Column(db.Integer, primary_key=True)
    Full_Name = db.Column(db.String(100), nullable = False)
    programs = db.relationship('Program', backref='lecturer_lookup', lazy=True)

class Program(db.Model):
    code = db.Column(db.String(10), primary_key=True)
    program_name = db.Column(db.String(100), nullable = False)
    Lec_PF_no = db.Column(db.Integer, db.ForeignKey('lecturer.PF_no'), nullable=False)
    elect = db.Column(db.String(100), nullable = False)
    timetable = db.relationship('Timetable', backref='program_lookup', lazy=True)

class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    timetable = db.relationship('Timetable', backref='venue_lookup', lazy=True)

class Period(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    timetable = db.relationship('Timetable', backref='period_lookup', lazy=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.Integer, db.ForeignKey('day.id'), nullable=False)
    study_class = db.Column(db.Integer, db.ForeignKey('study_class.id'), nullable=False)
    program = db.Column(db.String(100), db.ForeignKey('program.code'), nullable=False)
    venue = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    period = db.Column(db.Integer, db.ForeignKey('period.id'), nullable=False)


#End of database models

# default route
@app.route('/')
def index():
    #todo_list = Todo.query.all()
    #return str(todo_list)
    return redirect('https://bot.dialogflow.com/a35169f7-1379-46c7-91d3-1552e4d8c670')

def get_request():
    req = request.get_json(force=True)
    return req

def get_action():
    action = get_request().get('queryResult').get('action')
    return action

def get_time_id(t):
    if t <= 8:
        time_id = 1
    elif t <= 10:
        time_id = 2
    elif t <= 12:
        time_id = 3
    elif t <= 15:
        time_id = 4
    elif t <= 17:
        time_id = 5

    return time_id

# function for responses
def class_checker():
    # fetch action from json
    query_result = get_request().get('queryResult')

    day = query_result.get('parameters').get('days').upper()
    courses = query_result.get('parameters').get('courses').upper()
    year_of_study = query_result.get('parameters').get('year_of_study')
    time_t = query_result.get('parameters').get('time')
    time_hour = datetime.fromisoformat(time_t).hour

    if (time_hour in range(18,24)) or (time_hour in range(0,7)):
        responce = "Odd time, There is no class at that time"
    elif time_hour == 13:
        responce = "That is lunch hour. No classes until 2 pm"
    else:

        day_id = Day.query.filter_by(name=day).first().id
        get_study_class = Study_class.query.filter_by(course_name=courses, year_of_study=year_of_study).first().id

        class_checker = Timetable.query.filter_by(day=day_id, period=get_time_id(time_hour), study_class = get_study_class ).first()

        if class_checker:
            program_code = class_checker.program
            program_name = Program.query.filter_by(code=class_checker.program).first().program_name
            venue = Venue.query.filter_by(id=class_checker.venue).first().name
            responce = f'{program_code} {program_name}. Venue: {venue}'

        else:
            responce = "There is no class at that time"

    return {
        'fulfillmentText': responce,
        "source": "webhookdata"

    }

def get_who_teaches():
    #fetch results from json
    query_result = get_request().get('queryResult')
    unit = query_result.get('parameters').get('units').upper()

    program = Program.query.filter_by(code=unit).first()
    pf = program.Lec_PF_no
    Program_name = program.program_name.capitalize()

    lec_record = Lecturer.query.filter_by(PF_no=pf).first()
    lec_name = lec_record.Full_Name


    return {
        'fulfillmentText': unit + ' - ' + Program_name + ' is taught by '+ lec_name,
        "source": "webhookdata"
    }

def do_test():
    query_result = get_request().get('queryResult')
    time = query_result.get('parameters').get('time')

    return {
        'fulfillmentText': f'{time}',
        "source": "webhookdata"

    }



def get_units():
    query_result = get_request().get('queryResult')
    unit_type = query_result.get('parameters').get('unit_type').lower()
    year_of_study = query_result.get('parameters').get('year_of_study')
    courses = query_result.get('parameters').get('courses').upper()
    get_study_class = Study_class.query.filter_by(course_name=courses, year_of_study=year_of_study).first().id
    get_units = Timetable.query.filter_by(study_class=get_study_class).group_by(Timetable.program).all()
    if unit_type != 'all':
        filtered_courses = Program.query.filter_by(elect=unit_type).all()

        f_units = [k.code for k in filtered_courses]
        units = [unit.program for unit in get_units]
        final = [x for x in units if x in f_units]

        responce = f'{len(final)} inits: '
        for u in final:
            f = Program.query.filter_by(code=u).first().program_name
            responce += f'{u} {f}, '

    else:
        filtered_courses = Program.query.all()

        f_units = [k.code for k in filtered_courses]
        units = [unit.program for unit in get_units]

        responce = f'{len(units)} units: '
        for u in units:
            f = Program.query.filter_by(code=u).first().program_name
            responce += f'{u} {f}, '

    return {
        'fulfillmentText': responce,
        "source": "webhookdata"

    }

def time_checker():
    query_result = get_request().get('queryResult')
    unit = query_result.get('parameters').get('units').upper()

    timetable = Timetable.query.filter_by(program=unit).all()
    responce = ''
    for r in timetable:
        day = Day.query.filter_by(id=r.day).first().name
        venue = Venue.query.filter_by(id=r.venue).first().name
        period = Period.query.filter_by(id=r.period).first().name
        responce = responce + f'On {day} {period} in {venue},  '


    return {
        'fulfillmentText': responce,
        "source": "webhookdata"

    }

# create a route for webhook
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # return response
    if (get_action() == 'class_checker'):
        return make_response(jsonify(class_checker()))
    elif(get_action() == 'get_who_teaches'):
        return make_response(jsonify(get_who_teaches()))
    elif(get_action() == 'unit_checker'):
        return make_response(jsonify(get_units()))
    elif(get_action() == 'test_'):
        return make_response(jsonify(do_test()))
    elif(get_action() == 'time_checker'):
        return make_response(jsonify(time_checker()))

# run the app
if __name__ == '__main__':
    db.create_all()
    if 'liveconsole' not in gethostname():
        app.run()
