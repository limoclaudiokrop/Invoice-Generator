import os
import shutil
from flask import Flask, render_template,url_for,redirect,send_file,session
from flask_session import Session
import datetime 
from flask import request, make_response
from flask_sqlalchemy import SQLAlchemy
import smtplib
import ssl
from email.message import EmailMessage

from PyPDF2 import PdfFileReader, PdfFileWriter
import time
import zipfile
from io import BytesIO
import pdfkit
import sqlite3
import random
import json
from werkzeug.utils import secure_filename

from custom_funcs import create_invoice

conn = sqlite3.connect('church.db', check_same_thread=False)

c = conn.cursor()



app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config['UPLOAD_FOLDER'] = "static/documents"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://site.db'
db = SQLAlchemy(app)



@app.route("/tempdf")
def tempdf():
	data = ['Napoh Holdings Limited', '+254 733 402 463', 'info@napohholdingsltd.co.ke', 'P.O Box 201', 'Nairobi, Kenya', '00100']
	chec = "Check mate"
	rendered = render_template('invoicepdf.html', data=data, chec=chec)
	
	return rendered


@app.route("/convertpdf")
def convertpdf():
	rendered = render_template('invoicepdf.html')
	css = ['static/bootstrap.min.css', 'static/invoicepdf.css']
	pdf = pdfkit.from_string(rendered, False, css=css)

	response = make_response(pdf)
	response.headers['Content-Type'] = 'application/pdf'
	response.headers['Content-Disposition'] = 'attachment; filename=output.pdf'

	return response 


@app.route("/invoice")
def Invoice():
	if "user" not in session:
		session["user"] = None
	
	if session["user"] == None:
		return redirect("/")
	user = session["user"]
	welcome = "Welcome, " + user[1] + " " + user[2]
	return render_template("Invoice.html",  welcome=welcome)

@app.route("/add_invoice", methods =["GET", "POST"])
def add_invoice():
	if request.method == "POST":
		company_name = request.form.get("name")
		address = request.form.get("box")
		city = request.form.get("city")
		postal = request.form.get("postal")
		invoice_number = request.form.get("invoice_number")
		issue_date = request.form.get("issue_date")
		due_date = request.form.get("due_date")

		array = request.form.get("array")
		data = []
		arr1 = array.split(',')
		for a in arr1:
			a1 = a.split('-')
			data.append(a1)

		# print(data)
		# filepath = "static/documents/Ian.pdf"
		filepath = create_invoice(company_name,address,city,postal,invoice_number,issue_date,due_date,data)

	return send_file(filepath, as_attachment=True)

@app.route("/invoicefilename", methods =["GET", "POST"])
def checkInvoiceFilename():
	name = request.args['name']
	files = os.listdir("static/documents/Invoices")
	name = name + '.pdf'
	for f in files:
		if f == name:
			return "False"

	return 'True'

@app.route('/zipapp', methods =["GET", "POST"])
def ZipApplication():
	path = request.form.get("root")
	apps = path.split('/')
	appName = apps[len(apps)-1]
	
	fileName = appName + ".zip"
	memory_file = BytesIO()
	file_path = "/" + path
	print(file_path) 
	with zipfile.ZipFile(memory_file,'w',zipfile.ZIP_DEFLATED) as zipf:
		files = os.listdir(path)
		for file in files:
				zipf.write(os.path.join(path, file), arcname=file)

		
	memory_file.seek(0)
	return send_file(memory_file, attachment_filename=fileName, as_attachment=True)





@app.route("/selectfile", methods =["GET", "POST"])
def selectFile():
	
	data = request.get_json()
	path = data['path']
	file = data['file']
	filename = data['filename']
	original = filename
	position = data['position']
	for i in range(21):
		if os.path.exists(path +"/" + filename):
			filename = str(i) + original
		else:
			break

	#os.rename(path +"/" + original, path +"/" + filename)
	shutil.copy(file, path + "/" + filename)

	# if os.path.exists(path +"/" + filename):
	# 	#os.rename(path +"/" + filename, path +"/*" + filename)
	# 	shutil.copy(file, path +"/_" + filename)
	# 	filename = "_" + filename
	# else:
	# 	shutil.copy(file, path)	

	insertfilepath(path, filename, int(position))
	return path

@app.route("/renderinvoice", methods =["GET", "POST"])
def renderinvoice():
	filename = request.args["name"]
	invoice = getInvoiceByName(filename)
	data = json.loads(invoice[2])

	return render_template("invoicepdf.html", data=data)

@app.route("/postinvoice", methods =["GET", "POST"])
def postinvoice():
	
	data = request.get_json()
	filename = data['filename'].strip()
	rendered = render_template('invoicepdf.html', data=data)
	css = ['static/invoicepdf.css', 'static/bootstrap.min.css']
	pdf = pdfkit.from_string(rendered, 'static/documents/Invoices/'+filename+'.pdf', css=css)
	
	return 'success'


@app.route("/uploadfile", methods =["GET", "POST"])
def uploadFile():
	if "user" not in session:
		session["user"] = None
	
	if session["user"] == None:
		return redirect("/")
	 
	file = request.files['file']
	filename = secure_filename(file.filename)
	mypath = request.form.get("path")
	original = filename

	for i in range(1,21):
		if os.path.exists(mypath +"/" + filename):
			filename = str(i) + original
		else:
			break

	# path = mypath +"/" + filename
	# if os.path.exists(path):
	# 	filename = "1" + filename

	file.save(os.path.join(mypath, filename))
	return redirect("/storage?doc=" + mypath)	

@app.route("/checkfilename", methods =["GET", "POST"])
def checkfilename():
	path = request.args["path"]
	if os.path.exists(path):
		return 'false'
	return 'true'



@app.route("/renamefile", methods =["GET", "POST"])
def renameFile():
	if "user" not in session:
		session["user"] = None
	
	if session["user"] == None:
		return redirect("/")
	newName = request.form.get("filename")
	root = request.form.get("root")
	prev = request.form.get("path")
	cat = request.form.get("cat")
	prevname = request.form.get("prevname")
	temp_root = root
	if cat == "file":
		root = root + "/" + newName + ".pdf"
	else:
		root = root + "/" + newName

	os.rename(prev, root)

	myfile = getFileRootName(temp_root, prevname)
	if myfile != None:
		renamefile(myfile[0], newName+".pdf")

	return redirect("/storage?doc="+temp_root)	








if __name__ == '__main__':
	app.run(debug=True)