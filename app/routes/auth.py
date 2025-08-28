"""Authentication routes"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('auth/login.html')

        try:
            user = User.find_by_username(username)

            if user and User.verify_password(user, password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session['role'] = user['role']
                session['name'] = user['name']
                session['site_id'] = user['site_id']

                if user['role'] == 'vendor':
                    session['manager_id'] = user.get('manager_id')
                    session['vendor_company'] = user.get('vendor_company')

                session.permanent = True

                flash(f'Welcome back, {user["name"]}!', 'success')

                if user['role'] == 'vendor':
                    return redirect(url_for('vendor.dashboard'))
                elif user['role'] == 'manager':
                    return redirect(url_for('manager.dashboard'))
                elif user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('index'))

            else:
                flash('Invalid username or password', 'error')

        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Password reset"""
    if request.method == 'POST':
        flash('Password reset functionality not implemented yet', 'info')
    return render_template('auth/reset_password.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password"""
    if request.method == 'POST':
        flash('Password change functionality not implemented yet', 'info')
    return render_template('auth/change_password.html')

@auth_bp.route('/profile')
def profile():
    """User profile"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.find_by_id(session['user_id'])
    return render_template('auth/profile.html', user=user)
