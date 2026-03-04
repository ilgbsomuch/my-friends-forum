import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-99')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'forum.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='posts')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='post', lazy=True, cascade="all, delete-orphan")

    @property
    def score(self):
        return sum(v.value for v in self.votes)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')

login_manager = LoginManager(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    cat = request.args.get('category', 'Allgemein')
    posts = Post.query.filter_by(category=cat).order_by(Post.timestamp.desc()).all()
    user_votes = {}
    if current_user.is_authenticated:
        votes = Vote.query.filter_by(user_id=current_user.id).all()
        user_votes = {v.post_id: v.value for v in votes}
    return render_template('index.html', posts=posts, current_cat=cat, user_votes=user_votes)

@app.route('/register', methods=['POST'])
def register():
    u, p = request.form.get('username'), request.form.get('password')
    if User.query.filter_by(username=u).first():
        flash("Name vergeben!")
    else:
        new_user = User(username=u, password=p)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
    return redirect(url_for('index', category=request.form.get('category', 'Allgemein')))

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=request.form.get('username')).first()
    if user and user.password == request.form.get('password'):
        login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    cat = request.form.get('category')
    db.session.add(Post(content=request.form.get('content'), category=cat, author=current_user))
    db.session.commit()
    return redirect(url_for('index', category=cat))

@app.route('/vote/<int:post_id>/<string:direction>')
@login_required
def vote(post_id, direction):
    val = 1 if direction == 'up' else -1
    v = Vote.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if not v:
        db.session.add(Vote(value=val, user_id=current_user.id, post_id=post_id))
    elif v.value != val:
        v.value = val
    db.session.commit()
    return redirect(url_for('index', category=Post.query.get(post_id).category))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    db.session.add(Comment(content=request.form.get('content'), post_id=post_id, author=current_user))
    db.session.commit()
    return redirect(url_for('index', category=Post.query.get(post_id).category))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)