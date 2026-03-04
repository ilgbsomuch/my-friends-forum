import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__, template_folder='.')
# Security: Use the environment variable if available, else fallback
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-99')

# Absolute path for the DB file ensures it works on cloud servers
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'forum.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='posts')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')

# --- AUTH & DB INITIALIZATION ---
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# FIX: This block now runs even when using Gunicorn/Production servers
with app.app_context():
    db.create_all()

# --- ROUTES ---
@app.route('/')
def index():
    # Wrap in try/except to handle database lock issues on some hosts
    try:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
    except:
        posts = []
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['POST'])
def register():
    u, p = request.form.get('username'), request.form.get('password')
    if User.query.filter_by(username=u).first():
        flash("Username taken!")
    else:
        new_user = User(username=u, password=p)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=request.form.get('username')).first()
    if user and user.password == request.form.get('password'):
        login_user(user)
    else:
        flash("Invalid Login")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    db.session.add(Post(content=request.form.get('content'), author=current_user))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    db.session.add(Comment(content=request.form.get('content'), post_id=post_id, author=current_user))
    db.session.commit()
    return redirect(url_for('index'))

# This block is only for local testing (python app.py)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)