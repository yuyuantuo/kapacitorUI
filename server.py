import os
from flask import Flask, request, render_template, g, redirect, Response
from flask import session
import socket
import MySQLdb

ip = socket.gethostbyname(socket.gethostname())
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

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

  if constraint != '':
    where = '        .where(' + constraint + ')\n'

  if groupBy != '':
    group = '    .groupBy(\'' + groupBy + '\')\n'
    group2 = ': {{ .Group }}'

  if period != '' and every !='':
    window = '    .window()\n        .period(' + period + 'm)\n        .every(' + every + 'm)\n'

  if warn_cond == '>':
    warn_sign = 'larger'
  elif warn_cond == '<':
    warn_sign = 'smaller'

  if crit_cond == '>':
    crit_sign = 'larger'
  elif crit_cond == '<':
    crit_sign = 'smaller'

  if evaluation != '':
    eva = '    .eval(' + evaluation + ')\n        .as(\'' + evaluation2 + '\')\n'
  begining = '// alert if ' + description + '\n//\n// how to run:\n//  $kapacitor define -name ' + alert_name + ' -type stream -dbrp ' + database + '.default -tick /work/kapacitor/' + alert_name + '.tick\n//  $kapacitor enable ' + alert_name + '\n//\n\n'
  fro = 'stream\n    .from()\n        .database(\'' + database + '\')\n        .retentionPolicy(\'default\')\n        .measurement(\'' + measurement + '\')\n' + where
  alert = '    .alert()\n        .id(\'kapacitor/{{ .TaskName }}' + group2 + '\')\n        // Email subject\n        .message(\'[{{ .Level }}] {{ .ID }}\')\n        //Email body as HTML\n        .details(\'\'\'\n'
  detail = 'This is an auto generated email from Kapacitor. <br><br>\n\nKapacitor detects ' + description + ' on host <b>{{ index .Tags "host" }}</b>. <br><br>\n\n' + warn + ' is <b>{{ index .Fields \"' + warn + '\" }}</b>. <br>\n[WARNING] if ' + warn_sign + ' than ' + warn_value + ', and [CRITICAL] if ' + crit_sign + ' than ' + crit_value + '. <br><br>\n\n'
  detail2 = 'Data source: influxdb (database=\'' + database + '\', measurement=\'{{ .Name }}\')\n\'\'\')\n        .warn(lambda: \"' + warn + '\" ' + warn_cond + ' ' + warn_value + ')\n        .crit(lambda: \"' + crit + '\" ' + crit_cond + ' ' + crit_value + ')\n        .log(\'/tmp/kapacitor_' + alert_name + '.log\')\n        .email(\'' + email + '\')'
  content = begining + fro + group + window + eva + alert + detail + detail2
  print content
  cursor.execute("insert into kapacitor_config values ('%s','%s','%s');" %(alert_name,ip,content))  
  conn.commit()
  conn.close()
  return redirect('/')

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
