from flask import render_template, redirect, url_for, session, current_app, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from . import accounts_bp
from .forms import LoginForm, ChangePasswordForm

from utils import login_required
from .models import User

@accounts_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('start'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@accounts_bp.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('accounts.login'))

@accounts_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if 'username' not in session:
        return redirect(url_for('accounts.login'))

    form = ChangePasswordForm()
    if form.validate_on_submit():
        username = session['username']
        current_password = form.current_password.data
        new_password = form.new_password.data

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect.', 'danger')
        else:
            hashed = generate_password_hash(new_password)
            current_app.mongo.db.users.update_one({'username': username}, {'$set': {'password': hashed}})
            flash('Password changed successfully.', 'success')
            return redirect(url_for('index'))
    return render_template('change_password.html', form=form)
