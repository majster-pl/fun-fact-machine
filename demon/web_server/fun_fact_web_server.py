import os
from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import sqlite3

def create_app():
    current_file_path = os.path.abspath(__file__)
    root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
    _db_path = os.path.join(root_path, "src", "facts.db")
    db_path = "sqlite:///" + os.path.join(root_path, "src", "facts.db")

    # print("db_path", db_path)

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    # Dummy user data for demonstration
    users = {'admin': {'username': 'admin', 'password': 'onebigcircle'}}

    class User(UserMixin):
        def __init__(self, user_id):
            self.id = user_id

    class Fact(db.Model):
        __tablename__ = 'facts' 
        id = db.Column(db.Integer, primary_key=True)
        category = db.Column(db.String(255))
        description = db.Column(db.Text)
        times_used = db.Column(db.Integer, default=0)

    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)

    class LoginForm(FlaskForm):
        username = StringField('Username', validators=[DataRequired()])
        password = PasswordField('Password', validators=[DataRequired()])
        submit = SubmitField('Login')

    # Step 1: Define a SQLAlchemy model
    class Entry(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        category = db.Column(db.String(50), nullable=False)
        description = db.Column(db.Text, nullable=False)
        times_used = db.Column(db.Integer, nullable=False)
        owner = db.Column(db.Text, nullable=False)
        create_ts = db.Column(db.Integer, nullable=False)
        update_ts = db.Column(db.Integer, nullable=False)

    # Step 2: Create a form
    class EntryForm(FlaskForm):
        category = StringField('Category', validators=[DataRequired()])
        description = StringField('Fact', validators=[DataRequired()])        
        submit = SubmitField('Add New Fact')

    def update_data_in_db(id, column_name, new_value):
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        cursor.execute(f'UPDATE facts SET {column_name} = ? WHERE id = ?', (new_value, id))
        conn.commit()
        conn.close()

    def add_data_to_db(category, description):
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        cursor.execute(f'INSERT INTO facts (category, description, times_used, owner, create_ts, update_ts) VALUES (?, ?, ?, ?, ?, ?)', (category, description, 0, "admin", 0, 0))
        conn.commit()
        conn.close()

    @app.route('/')
    @login_required
    def index():
        # return 'Welcome to the home page!'
        facts = Fact.query.all()
        return render_template('index.html', data=facts)
    
    @app.route('/add_entry', methods=['GET', 'POST'])
    @login_required
    def add_entry():
        form = EntryForm()

        if form.validate_on_submit():
            # Create a new Entry instance and add it to the database
            # new_entry = Entry(category=form.category.data, description=form.description.data, times_used=0, owner="admin", create_ts=0, update_ts=0)
            # db.session.add(new_entry)
            # db.session.commit()
            try:
                add_data_to_db(form.category.data, form.description.data)
                # return jsonify({'success': True, 'message': 'New fact added successfully!'})
                return redirect(url_for('index'))
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)})

            # return redirect(url_for('view_entries'))

        return render_template('add_entry.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            # If the user is already logged in, redirect them to the home page
            return redirect(url_for('index'))

        form = LoginForm()

        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            user = users.get(username)

            if user and user['password'] == password:
                login_user(User(username))
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Login failed. Check your username and password.', 'danger')

        return render_template('login.html', form=form)

    @app.route('/update/<int:id>', methods=['POST'])
    def update(id):
        try:
            data = request.json
            print("DATA:", type(data))
            for column in data:
                value = data[column]
                if value:
                    update_data_in_db(id, column, value)

            # update_data_in_db(id, 'email', data['email'])
            # Add other columns as needed

            return jsonify({'success': True, 'message': 'Data updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logout successful!', 'success')
        return redirect(url_for('index'))

    return app

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=False, host='0.0.0.0')
