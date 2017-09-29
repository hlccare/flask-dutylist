#-*- coding: utf-8 -*-
#encoding=utf-8
import sys
from flask import Flask , render_template , session , url_for , flash , redirect , request
from flask_bootstrap import Bootstrap
from flask_script import Manager
from flask_moment import Moment
from flask_wtf import FlaskForm
from flask_mail import Mail , Message
# import FlaskForm
from wtforms import TextAreaField , StringField , SubmitField , PasswordField , ValidationError
from wtforms.validators import DataRequired , Length , EqualTo
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin , login_required , LoginManager , login_user , logout_user , current_user
import os

reload(sys)
sys.setdefaultencoding('utf8')
baseDir = os.path.abspath(os.path.dirname(__file__))
print baseDir
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hl'
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_POST'] = '465'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(baseDir , 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager()
login_manager.init_app(app)
bootstrap = Bootstrap(app)
manager = Manager(app)
moment = Moment(app)
mail = Mail(app)
db = SQLAlchemy(app)
text_factory = str


class NameForm(FlaskForm):
	name = StringField('名字？', validators = [DataRequired()] )
	submit = SubmitField('提交')

class LoginForm(FlaskForm):
	username = StringField('用户名',validators = [DataRequired() , Length(1 , 64)])
	password = PasswordField('密码' , validators = [DataRequired()])
	submit = SubmitField('登录')

class RegisterForm(FlaskForm):
	username = StringField('用户名',validators = [DataRequired() , Length(1 , 64)])
	password = PasswordField('密码' , validators = [DataRequired()])
	password2 = PasswordField('再次输入密码' , validators = [DataRequired() , EqualTo('password' , message = '两次输入密码不一致')])
	submit = SubmitField('注册')

	def validate_username(self , field):
		if User.query.filter_by(username = field.data).first():
			raise ValidationError('此用户名已被使用')
class DutyForm(FlaskForm):
	content = TextAreaField('内容',validators = [DataRequired()])
	category = StringField('类目' , validators = [DataRequired() , Length(1,32)])
	submit = SubmitField('添加')

class User(UserMixin , db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer , primary_key = True)
	username = db.Column(db.String(64) , unique = True , index = True)
	password = db.Column(db.String(64) , unique = True , index = True)
	duty = db.relationship('Duty' , backref = 'author' , lazy = 'dynamic')
	def __repr__(self):
		return '<User %r>' % self.username

class Duty(db.Model):
	__tablename__ = 'duty'
	id = db.Column(db.Integer , primary_key =True)
	# content = db.Column(db.Text)
	content = db.Column(db.String(120))
	category = db.Column(db.String(64) , index = True)
	done = db.Column(db.Boolean , default = False)
	timestamp = db.Column(db.DateTime , index = True , default = datetime.utcnow)
	author_id = db.Column(db.Integer , db.ForeignKey('users.id'))

	def __repr__(self):
		return '<Duty %r>' % self.content

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))
@app.route('/')
def index():


	return render_template('index.html', current_time = datetime.utcnow())
# @app.route('/user/<name>')
# def user(name):
# 	return render_template('user.html' , name = name)
@app.route('/register' , methods = ['GET' , 'POST'])
def register():
	registerForm = RegisterForm()
	if registerForm.validate_on_submit():
		user = User(username = registerForm.username.data , password = registerForm.password.data)
		db.session.add(user)
		flash('注册完成，现可登入')
		return redirect(url_for('login'))
	return render_template('register.html' , form = registerForm)
@app.route('/login' , methods = ['GET' , 'POST'])
def login():
	loginForm = LoginForm()
	if loginForm.validate_on_submit():
		user = User.query.filter_by(username = loginForm.username.data).first()

		if user is not None and loginForm.password.data == user.password:
			login_user(user)
			return redirect(request.args.get('next') or url_for('index'))
		else:
			flash('用户不存在或密码错误！请重新输入')
	return render_template('login.html', form = loginForm)
@app.route('/logout')
def logout():
	logout_user()
	flash('已成功登出')
	return render_template('logout.html')

@app.route('/changeduty/<int:dutyid>')
@login_required
def changeduty(dutyid):
     user = User.query.get_or_404(current_user.id)
     duty = user.duty.filter_by(id=dutyid).first()
     duty.done=True
     db.session.commit()
     flash('已成功修改一项事务')
     return redirect(url_for('dutylist'))


@app.route('/deleteduty/<int:dutyid>')
@login_required
def deleteduty(dutyid):
     user = User.query.get_or_404(current_user.id)
     duty = user.duty.filter_by(id=dutyid).first()
     db.session.delete(duty)
     db.session.commit()
     flash('已成功删除一项事务')
     return redirect(url_for('dutylist'))

@app.route('/dutylist' , methods = ['GET' , 'POST'])
@login_required
def dutylist():
	user = User.query.get_or_404(current_user.id)
	select_category = None
	if user is None:
		abort(404)
	else:
		duty = user.duty.order_by(Duty.timestamp.asc()).all()
		categoryList = []
		for term in duty:
			categoryList.append(term.category)
		categoryList=list(set(categoryList))
		if request.method == 'GET' and request.args.get('select_category'):
			select_category = request.args.get('select_category')
			duty = user.duty.filter_by(category = select_category).all()
			
		# sql='SELECT DISTINCT category FROM duty,users where users.username=\'%s\' and duty.author_id=%s'%(user.username,user.id)
		# categoryList = db.session.execute(sql).fetchall()
		
	return render_template('dutylist.html', duty = duty , categoryList = categoryList , select_category = select_category)
@app.route('/addduty' , methods = ['GET' , 'POST'])
@login_required
def addduty():
	dutyForm = DutyForm()
	user = User.query.get_or_404(current_user.id)
	if user is None:
		abort(404)
	if dutyForm.validate_on_submit():
		newDuty = Duty(content = dutyForm.content.data , category = dutyForm.category.data , done = 0)
		newDuty.author_id = user.id
		db.session.add(newDuty)
		db.session.commit()
		return redirect(url_for('dutylist'))
	return render_template('addduty.html' , form = dutyForm)
@app.route('/secret')
@login_required
def secret():
	return "未认证用户！"
@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'),404

if __name__ == '__main__':
	# app.run(debug = True)
	manager.run()