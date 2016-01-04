from flask import Flask, render_template, send_file, g, abort
import os
from apscheduler.schedulers.background import BackgroundScheduler
import tempfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import urllib2
from collections import deque
import datetime
import sqlite3

DATABASE = 'db_test.db'
app = Flask(__name__)

global data_list_u
data_list_u = deque([None] * 100)

def connect_to_database():
    return sqlite3.connect(DATABASE)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_data_users():
	global data_list_u
	response = urllib2.urlopen('http://www.mediavida.com')
	data = response.read()
	start = data.find('/online">')
	end = data.find('</a>', start)
	data = int(data[start+9:end])
	data_list_u.popleft()
	data_list_u.append(data)

def get_data_temp():
	response = urllib2.urlopen('http://www.meteoclimatic.net/perfil/ESMAD2800000028037A')
	data = response.read()
	start = data.find('dadesactuals">')
	end = data.find(' ', start)
	data = float(data[start+14:end])
	
	_time = datetime.datetime.now().time()
	curr_time = str(_time).split(':')[0] + ':' + str(_time).split(':')[1]
	
	t = (curr_time, data)
	
	db = sqlite3.connect('db_test.db')
	cur = db.cursor()
	cur.execute("insert into temperatura (f1, f2) values (?,?)", t) 
	db.commit()

@app.before_first_request
def initialize():
	apsched = BackgroundScheduler()
	apsched.add_job(get_data_users, 'interval', seconds=5, replace_existing=True)
	apsched.add_job(get_data_temp, 'interval', hours=1, replace_existing=True)
	apsched.start()

@app.route('/')
def index():
	response = urllib2.urlopen('http://www.imgur.com/random')
	data = response.read()
	start = data.find('http://i.imgur.com')
	end = data.find('.', start+len('http://i.imgur.com'))
	data = data[start:end+4]
	return render_template('page.html', name='Inicio', img=data)
	
@app.route('/users')
def plot_data_users():
	try:
		_file = os.listdir('static/temp')[0]
		os.remove('static/temp/' + _file)
	except Exception as e:
		pass
		
	fig = plt.figure(figsize=(5,4), dpi=100)
	axes = fig.add_subplot(1,1,1)
	
	axes.plot(range(100), data_list_u)
	
	f = tempfile.NamedTemporaryFile(dir='static/temp', suffix='.png', delete=False)
	plt.savefig(f)
	f.close()
	pltPng = f.name.split('/')[-1]
	
	return(render_template('figures.html', name='Usuarios online', plotPng=pltPng))
	
@app.route('/temp')
def plot_data_temp():
	try:
		_file = os.listdir('static/temp')[0]
		os.remove('static/temp/' + _file)
	except Exception as e:
		pass
		
	fig = plt.figure(figsize=(5,4), dpi=100)
	axes = fig.add_subplot(1,1,1)
	
	data_list_t = []
	time_list_t = []
	
	cur = get_db().cursor()
	cur.execute("select * from temperatura")
	data = cur.fetchall()
	
	for i in range(len(data)):
		data_list_t.append(data[i][1])
		time_list_t.append(data[i][0])
	
	axes.plot(range(len(data_list_t)), data_list_t)
	plt.xticks(range(len(data_list_t)), time_list_t, size='small', rotation=60)
	
	f = tempfile.NamedTemporaryFile(dir='static/temp', suffix='.png', delete=False)
	plt.savefig(f)
	f.close()
	pltPng = f.name.split('/')[-1]
	
	return(render_template('figures.html', name='Temperatura', plotPng=pltPng))
	
'''	
@app.route('/<name>')
def old(name):
	return render_template('page.html', name=name, img="/static/temp/favicon.ico")
'''

@app.route('/list', defaults={'req_path': ''})
@app.route('/list/<path:req_path>')
def dir_listing(req_path):
    BASE_DIR = '/home/ubuntu/workspace'
    
    # Joining the base and the requested path
    abs_path = os.path.join(BASE_DIR, req_path)

    # Return 404 if path doesn't exist
    if not os.path.exists(abs_path):
        return abort(404)

    # Check if path is a file and serve
    if os.path.isfile(abs_path):
        return send_file(abs_path)

    # Show directory contents
    files = os.listdir(abs_path)
    return render_template('list.html', files=files)


if __name__ == '__main__':
	port = int(os.environ.get('PORT', 8080))
	app.run(debug=True, host='0.0.0.0', port=port)
