## SI 364
## Fall 2017
## Final
## Hailey Patterson
import os
from flask import Flask, request, render_template, redirect, url_for, flash, json, make_response
from datetime import datetime
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError, TextAreaField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo, NumberRange
import requests
import random
from threading import Thread
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_mail import Mail, Message
from threading import Thread
from werkzeug import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'si364beerfinalapphardtoguessstring'
app.debug = True 
app.static_folder = 'static'

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/haileypaSI364Final"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587 #default
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') 
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_SUBJECT_PREFIX'] = '[Beers and Breweries App]'
app.config['MAIL_SENDER'] = 'Admin <haileysi364@gmail.com>' 
app.config['ADMIN'] = os.environ.get('ADMIN') or "Admin <haileysi364@gmail.com>"

# Set up Flask debug stuff
manager = Manager(app)
db = SQLAlchemy(app) # For database use
migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand) # Add migrate
mail = Mail(app) 

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) # set up login manager
## Set up Shell context so it's easy to use the shell to debug
def make_shell_context():
    return dict(app=app, db=db, beers=beers, breweries=breweries, users=users)
### function use to manager
manager.add_command("shell", Shell(make_context=make_shell_context))

####Send Email Functions
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg]) 
    thr.start()
    return thr 


# Association table - Beers and collection
user_beer = db.Table('collection_beers',db.Column('beer_id', db.Integer, db.ForeignKey('beers.id')),db.Column('collection_id',db.Integer, db.ForeignKey('personalBeer.id')))

# Association table - Brewery and Collection
user_brewery = db.Table('collection_breweries',db.Column('brewery_id', db.Integer, db.ForeignKey('breweries.id')),db.Column('collection_id',db.Integer, db.ForeignKey('personalBrewery.id')))


#####Models####

# User model
class User(UserMixin, db.Model):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(225), unique=True, index=True)
	email = db.Column(db.String(64), unique=True, index=True)
	age = db.Column(db.Integer())
	beer_collection = db.relationship('PersonalBeer', backref='User')
	brewery_collection = db.relationship('PersonalBrewery', backref='User')
	password_hash = db.Column(db.String(128))

	@property
	def password(self):
	    raise AttributeError('password is not a readable attribute')

	@password.setter
	def password(self, password):
	    self.password_hash = generate_password_hash(password)

	def verify_password(self, password):
	    return check_password_hash(self.password_hash, password)

	@property
	def is_authenticated(self):
	    return True

	@property
	def is_active(self):
	    return True

#Saved Beer model
class PersonalBeer(db.Model):
    __tablename__ = "personalBeer"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    beers = db.relationship('Beer',secondary=user_beer,backref=db.backref('personalBeer',lazy='dynamic'),lazy='dynamic')

#Saved Brewery model
class PersonalBrewery(db.Model):
    __tablename__ = "personalBrewery"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    breweries = db.relationship('Brewery',secondary=user_brewery,backref=db.backref('personalBrewery',lazy='dynamic'),lazy='dynamic')

####Beer model
class Beer(db.Model):
    __tablename__ = "beers"
    id = db.Column(db.Integer, primary_key=True)
    beer_name = db.Column(db.String(285))
    abv = db.Column(db.Float())
    description = db.Column(db.String(1500))
    style = db.Column(db.String(285))

    def __repr__(self):
        return "{}, (ID: {})".format(self.beer_name,self.id)

# Brewery model
class Brewery(db.Model):
    __tablename__ = 'breweries'
    id = db.Column(db.Integer, primary_key=True) ## -- id (Primary Key)
    brewery_name = db.Column(db.String(285))
    website = db.Column(db.String(285))
    description = db.Column(db.String(5000))

    def __repr__(self):
        return "{} (ID: {})".format(self.brewery_name,self.id)

## DB load functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

####Forms####

class LoginForm(FlaskForm):
	username = StringField('Beer drinking alias:', validators=[ Required() ])
	password = PasswordField('Password:', validators=[ Required() ])
	remember_me = BooleanField('Keep me logged in')
	submit = SubmitField('Login')

class CreateAccountForm(FlaskForm):
	username = StringField('Beer Drinking Alias:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
	password = PasswordField('Password:',validators=[Required(),EqualTo('confirmPassword',message="Passwords must match")])
	confirmPassword = PasswordField('Confirm Password:', validators=[ Required() ])
	email = StringField('Email:', validators=[Required(),Length(1,64),Email(message='Please enter a valid email!')])
	age = IntegerField('Age:', validators=[ Required(), NumberRange(min=21, max=None, message='You must be at least 21!') ])
	submit = SubmitField('Create Account')

	def validate_email(self,field):
	    if User.query.filter_by(email=field.data).first():
	        raise ValidationError('Email already registered.')

	def validate_username(self,field):
	    if User.query.filter_by(username=field.data).first():
	        raise ValidationError('Username already taken')

class UserForm(FlaskForm):
	username = StringField('Enter your beer drinking alias:')
	submit = SubmitField('Submit and Search!')

class SearchBeerForm(FlaskForm):
    beer = StringField('Enter a beer:')
    submit = SubmitField('Search Beers!')

class SaveBeerForm(FlaskForm):
	name = StringField('Beer List Name:', validators=[ Required() ])
	submit = SubmitField('Create Beer List!')

class SearchBreweryForm(FlaskForm):
    brewery = StringField('Enter a brewery:', validators=[ Required() ])
    submit = SubmitField('Search Breweries!')

class SaveBreweryForm(FlaskForm):
	name = StringField('Brewery List Name:', validators=[ Required() ])
	submit = SubmitField('Create Brewery List!')

####get_or_create_functions
def get_beer_by_id(id):
    beer = Beer.query.filter_by(id=id).first()
    return beer
def get_beer_list_by_id(id):
	l = PersonalBeer.query.filter_by(id=id).first()
	return l

def get_beers_in_list(list_of_lists):
	beers_in_collections = {}
	for l in list_of_lists:
		beers_in_collections[l] = Beer.query.join(user_beer, user_beer.c.beer_id == Beer.id).filter(user_beer.c.collection_id == l.id).all()
	return beers_in_collections

def get_brewery_by_id(id):
    brewery = Brewery.query.filter_by(id=id).first()
    return brewery
def get_brewery_list_by_id(id):
	l = PersonalBrewery.query.filter_by(id=id).first()
	return l

def get_breweries_in_list(list_of_lists):
	breweries_in_collections = {}
	for l in list_of_lists:
		breweries_in_collections[l] = Brewery.query.join(user_brewery, user_brewery.c.brewery_id == Brewery.id).filter(user_brewery.c.collection_id == l.id).all()
	return breweries_in_collections

def get_or_create_beer(db_session, beer_name, abv, description, style):
    beer = db_session.query(Beer).filter_by(beer_name = beer_name).first()
    if beer:
    	return beer
    else:
    	beer = Beer(beer_name=beer_name, abv=abv, description=description, style=style)
    	db_session.add(beer)
    	db_session.commit()
    	return beer

def get_or_create_brewery(db_session, brewery_name, website, description):
    brewery = db_session.query(Brewery).filter_by(brewery_name = brewery_name).first()
    if brewery:
        return brewery
    else:
        brewery = Brewery(brewery_name=brewery_name, website=website, description=description)
        db_session.add(brewery)
        db_session.commit()
        return brewery

def get_or_create_beer_collection(db_session, name, beer_list, current_user):
    beerCollection = db_session.query(PersonalBeer).filter_by(name=name,user_id=current_user.id).first()
    if beerCollection:
        return beerCollection
    else:
        beerCollection = PersonalBeer(name=name,user_id=current_user.id,beers=[])
        for beer in beer_list:
            beerCollection.beers.append(beer)
        db_session.add(beerCollection)
        db_session.commit()
        return beerCollection

def get_or_create_brewery_collection(db_session, brewery_name, brewery_list, current_user):
    breweryCollection = db_session.query(PersonalBrewery).filter_by(name=brewery_name,user_id=current_user.id).first()
    if breweryCollection:
        return breweryCollection
    else:
        breweryCollection = PersonalBrewery(name=brewery_name,user_id=current_user.id,breweries=[])
        for brewery in brewery_list:
            breweryCollection.breweries.append(brewery)
        db_session.add(breweryCollection)
        db_session.commit()
        return breweryCollection

@app.route('/', methods= ['POST','GET'])
def hello_beer_world():
	beerForm = SearchBeerForm()
	breweryForm = SearchBreweryForm()
	loginForm = LoginForm(request.form)
	if request.method == 'POST':
		if loginForm.validate_on_submit():
			user = User.query.filter_by(username=loginForm.username.data).first()
			if user is not None and user.verify_password(loginForm.password.data):
				login_user(user, loginForm.remember_me.data)
				return render_template("search_form.html", beerForm=beerForm, breweryForm=breweryForm, username=request.form['username'])
		flash('Invalid username or password.')
	return render_template('home.html', form=loginForm)

@app.route('/newaccount', methods= ['POST','GET'])
def new_account():
	form = CreateAccountForm()
	if request.method == 'POST':
		if form.validate_on_submit():
			user = User(username=form.username.data, password=form.password.data, email=form.email.data, age=form.age.data)
			db.session.add(user)
			db.session.commit()
			flash('You can now log in!')
			return redirect(url_for('hello_beer_world'))	
	return render_template("new_account.html", form=form )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('hello_beer_world'))

@app.route('/search', methods= ['POST','GET'])
def search():
	beerForm = SearchBeerForm()
	breweryForm = SearchBreweryForm()
	return render_template("search_form.html", beerForm= beerForm, breweryForm=breweryForm)


@app.route('/beerinfo', methods= ['POST','GET'])
def beer_info():
	base_url = "http://api.brewerydb.com/v2/beers"
	params = {}
	now = datetime.now().time()
	today5pm = now.replace(hour=17, minute=0, second=0, microsecond=0)
	form = SearchBeerForm(request.form)
	if request.method == 'POST':
		if form.validate_on_submit():
			name = form.beer.data
			params['name'] = name
			params['key'] = '01d35c18b7ed7936d4e01e7cb83eb0ee'
			r = requests.get(base_url, params= params).json()
			if 'data' in r.keys():
				data = r['data']
				for r in data:
					if 'name' in r.keys():
						name = r['name']
					else:
						name = ''
					if 'abv' in r.keys():
						abv = r['abv']
					else:
						abv = '0.0'
					if 'description' in r.keys():
						description = r['description']
					else:
						description = ''
					if 'style' in r.keys():
						style = r['style']['name']
					else:
						style = ''
					beer = get_or_create_beer(db.session, name, abv, description, style)
				return render_template("beer_info.html", data=data, name=name, current_time=datetime.now(), today5pm=today5pm, form=form)
			else:
				data = 'NULL'

			return render_template("beer_info.html", data=data, name=name, current_time=datetime.now(), today5pm=today5pm, form=form)

	flash("ERROR:You didn't enter anything!")	
	return redirect(url_for('search'))

@app.route('/beerlist', methods=['GET', 'POST'])
def create_beer_list():
	form = SaveBeerForm()
	all_beers = [] 
	beers = Beer.query.all()
	for beer in beers:
		all_beers.append((beer.beer_name, beer.abv, beer.description, beer.style, beer.id))
	all_beers.sort()
	if request.method == "POST" and form.validate_on_submit():
		selected_beers = request.form.getlist("beers")
		beer_objects = [get_beer_by_id(int(id)) for id in selected_beers]
		get_or_create_beer_collection(db.session, current_user=current_user, name=form.name.data, beer_list=beer_objects)
		return redirect(url_for('my_beer_lists'))
	return render_template('beer_list.html', all_beers=all_beers, current_time=datetime.now(), form=form)


@app.route('/mybeerlists', methods= ['POST','GET'])
def my_beer_lists():
	beers_in_collections = {}
	beers_in_collections_email = {}
	if current_user.is_authenticated:
		lists = PersonalBeer.query.filter_by(user_id=current_user.id).all()
		beers_in_collections= get_beers_in_list(lists)
		if request.method == "POST":
			selected_lists = request.form.getlist("lists")
			list_objects = [get_beer_list_by_id(int(id)) for id in selected_lists]
			beers_in_collections_email = get_beers_in_list(list_objects)
			if app.config['ADMIN']:
				send_email(app.config['ADMIN'], 'Beer Lists',
							'mail/beer_list', beers_in_collections=beers_in_collections_email)
				flash("Email Sent!")

	return render_template('my_beer_lists.html', beers_in_collections=beers_in_collections, current_time=datetime.now())


@app.route('/breweryinfo', methods= ['POST','GET'])
def brewery_info():
	base_url = "http://api.brewerydb.com/v2/search/"
	params = {}
	form = SearchBreweryForm(request.form)
	now = datetime.now().time()
	today5pm = now.replace(hour=17, minute=0, second=0, microsecond=0)
	if request.method == 'POST' and form.validate_on_submit():
		name = form.brewery.data
		params['q'] = name
		params['type'] = 'brewery'
		params['key'] = '01d35c18b7ed7936d4e01e7cb83eb0ee'
		r = requests.get(base_url, params= params).json()
		if 'data' in r.keys():
			data = r['data']
			for r in data:
				if 'name' in r.keys():
					name = r['name']
				else:
					name = ''
				if 'website' in r.keys():
					website = r['website']
				else:
					website = ''
				if 'description' in r.keys():
					description = r['description']
				else:
					description = ''
				brewery = get_or_create_brewery(db.session, name, website, description)
			return render_template("brewery_info.html", data=data, name=name, current_time=datetime.now(), today5pm=today5pm, form=form)
		else:
			data = 'NULL'
		
		return render_template("brewery_info.html", data=data, name=name, current_time=datetime.now(), today5pm=today5pm, form=form)
	flash("ERROR:You didn't enter anything!")	
	return redirect(url_for('search'))	

@app.route('/brewerylist', methods=['GET', 'POST'])
def create_brewery_list():
	form = SaveBreweryForm()
	all_breweries = [] 
	breweries = Brewery.query.all()
	for brewery in breweries:
		all_breweries.append((brewery.brewery_name, brewery.website, brewery.description, brewery.id))
	all_breweries.sort()
	if request.method == "POST" and form.validate_on_submit():
		selected_breweries = request.form.getlist("breweries")
		brewery_objects = [get_brewery_by_id(int(id)) for id in selected_breweries]
		get_or_create_brewery_collection(db.session, current_user=current_user, brewery_name=form.name.data, brewery_list=brewery_objects)
		return redirect(url_for('my_brewery_lists'))
	return render_template('brewery_list.html', all_breweries=all_breweries, current_time=datetime.now(), form=form)

@app.route('/mybrewerylists', methods= ['POST','GET'])
def my_brewery_lists():
	breweries_in_collections = {}
	breweries_in_collections_email = {}
	if current_user.is_authenticated:
		lists = PersonalBrewery.query.filter_by(user_id=current_user.id).all()
		breweries_in_collections= get_breweries_in_list(lists)
		if request.method == "POST":
			selected_lists = request.form.getlist("lists")
			list_objects = [get_brewery_list_by_id(int(id)) for id in selected_lists]
			breweries_in_collections_email = get_breweries_in_list(list_objects)
			if app.config['ADMIN']:
				send_email(app.config['ADMIN'], 'Brewery Lists',
							'mail/brewery_list', breweries_in_collections=breweries_in_collections_email)


	return render_template('my_brewery_lists.html', breweries_in_collections=breweries_in_collections, current_time=datetime.now())

@app.errorhandler(403)
def page_not_found(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500

@app.errorhandler(503)
def page_not_found(e):
    return render_template('503.html'), 503

if __name__ == '__main__':
	db.create_all()
	manager.run() 

