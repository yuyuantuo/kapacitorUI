import os
from flask import Flask, request, render_template, g, redirect, Response
from flask import session
import socket
import MySQLdb
from HTMLParser import HTMLParser

ip = socket.gethostbyname(socket.gethostname())
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = os.urandom(24)

print 'a'
conn = MySQLdb.connect("10.103.1.48","monitoruser","monitorpass","monitor")
print 'b'
cursor = conn.cursor()

@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print request.args
  msg = ''
  label = ''
  context = dict(data = msg, data2 = label)

  return render_template("index.html", **context)

@app.route('/add', methods=['POST'])
def add():
  where = ''
  group = ''
  group2 = ''
  window = ''
  eva = ''
  description=request.form['description']
  alert_name=request.form['alert_name']
  database=request.form['database']
  measurement = request.form['measurement']
  constraint=request.form['constraint']
  groupBy=request.form['groupBy']
  period=request.form['period']
  every=request.form['every']
  evaluation=request.form['evaluation']
  evaluation2 = request.form['evaluation2']
  warn=request.form['warn']
  warn_cond=request.form['warn_cond']
  warn_value=request.form['warn_value']
  crit=request.form['crit']
  crit_cond=request.form['crit_cond']
  crit_value=request.form['crit_value']
  email=request.form['email']

  cursor.execute('select alert_name from kapacitor_config')
  content = cursor.fetchall()
  for result in content:
    if result[0] == alert_name or not description or not alert_name or not database or not measurement or not warn or not warn_cond or not warn_value or not crit or not crit_cond or not crit_value or not email:
      return redirect('/create_fail')
  conn.commit()

  if constraint:
    where = '        .where(' + constraint + ')\n'

  if groupBy:
    group = '    .groupBy(\'' + groupBy + '\')\n'
    group2 = ': {{ .Group }}'

  if period and every:
    window = '    .window()\n        .period(' + period + 'm)\n        .every(' + every + 'm)\n'

  if warn_cond == '>':
    warn_sign = 'larger'
  elif warn_cond == '<':
    warn_sign = 'smaller'

  if crit_cond == '>':
    crit_sign = 'larger'
  elif crit_cond == '<':
    crit_sign = 'smaller'

  if evaluation:
    eva = '    .eval(' + evaluation + ')\n        .as(\'' + evaluation2 + '\')\n'
  
  template = """// alert if %(description)s
//
// how to run:
//  $kapacitor define -name %(alert_name)s -type stream -dbrp %(database)s.default -tick /work/kapacitor/%(alert_name)s.tick
//  $kapacitor enable %(alert_name)s
//

stream
    .from()
        .database('%(database)s')
        .retentionPolicy('default')
        .measurement('%(measurement)s')
%(where)s%(group)s%(window)s%(eva)s    .alert()
        .id('kapacitor/{{ .TaskName }}%(group2)s')
        // Email subject
        .message(\[{{ .Level }}] {{ .ID }}')
        //Email body as HTML
        .details('''
This is an auto generated email from Kapacitor. <br><br>

Kapacitor detects %(description)s on host <b>{{ index .Tags "host" }}</b>. <br><br>

%(warn)s is <b>{{ index .Fields "%(warn)s" }}</b>. <br>
[WARNING] if %(warn_sign)s than %(warn_value)s, and [CRITICAL] if %(crit_sign)s than %(crit_value)s. <br><br>

Data source: influxdb (database='%(database)s', measurement='{{ .Name }}')
''')
        .warn(lambda: "%(warn)s" %(warn_cond)s %(warn_value)s)
        .crit(lambda: "%(crit)s" %(crit_cond)s %(crit_value)s)
        .log('/tmp/kapacitor_%(alert_name)s.log')
        .email('%(email)s')"""

  content = template % locals()
  ctt = conn.escape_string(content)
  print ctt
  print ip

  cursor.execute('insert into kapacitor_config (alert_name,ip,content) values ("%s","%s","%s")' %(str(alert_name),str(ip),str(ctt))) 
  conn.commit()
  
  return redirect('/create_success')

@app.route('/create_success')
def create_success():
  return render_template("create_success.html")

@app.route('/create_fail')
def create_fail():
  return render_template("create_fail.html")

@app.route('/display')
def display():
  alerts = []
  cursor.execute('select alert_name from kapacitor_config')
  content = cursor.fetchall()
  print content
  for result in content:
    print result[0]
    alerts.append(result[0])
  conn.commit()

  context = dict(data = alerts)
  return render_template("display.html", **context)

@app.route('/display/<alert_name>')
def detail(alert_name):
  cursor.execute('select content from kapacitor_config where alert_name = "%s"' %alert_name)
  result = cursor.fetchone()
  content = result[0]
  session['alert_name'] = alert_name
  context = dict(data = content)
  conn.commit()
  return render_template("detail.html", **context)

@app.route('/change', methods = ['POST'])
def save_change():
  
  change = request.form['myTxt']
  change_fix = HTMLParser().unescape(change)
  print change_fix
  esc_change = conn.escape_string(change_fix)
  cursor.execute('update kapacitor_config set content = "%s" where alert_name = "%s"' %(esc_change,session['alert_name']))
  conn.commit()
  return redirect('/display/%s' %session['alert_name'])

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
