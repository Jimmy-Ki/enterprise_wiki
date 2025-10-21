from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Role, UserSession, Permission
from app.forms.auth import LoginForm, RegistrationForm, ChangePasswordForm, \
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm
from app.decorators import permission_required, admin_required
from app.email import send_email
import secrets
import hashlib

auth = Blueprint('auth', __name__)

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('wiki.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('wiki.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Check if account is locked
            if user.is_locked():
                flash('Account is temporarily locked due to multiple failed login attempts. Please try again later.', 'danger')
                return render_template('auth/login.html', form=form)

            if user.verify_password(form.password.data):
                # Check if user is active
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact administrator.', 'danger')
                    return render_template('auth/login.html', form=form)

                # Reset failed login attempts
                user.failed_login_attempts = 0
                user.unlock_account()
                db.session.add(user)

                # Create user session
                session_token = secrets.token_urlsafe(32)
                user_session = UserSession(
                    user_id=user.id,
                    session_token=session_token,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.add(user_session)
                db.session.commit()

                # Login user
                login_user(user, form.remember_me.data)
                next_page = request.args.get('next')
                if next_page is None or not next_page.startswith('/'):
                    next_page = url_for('wiki.index')
                flash('You have been logged in successfully.', 'success')
                return redirect(next_page)
            else:
                # Increment failed login attempts
                user.increment_failed_login()
                db.session.add(user)
                flash('Invalid email or password.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    # Revoke current session
    session_token = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
    if session_token:
        user_session = UserSession.query.filter_by(
            user_id=current_user.id,
            session_token=session_token,
            is_active=True
        ).first()
        if user_session:
            user_session.revoke()

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('wiki.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            name=form.name.data
        )
        db.session.add(user)
        db.session.commit()

        # Send confirmation email (with error handling)
        email_sent = False
        try:
            token = user.generate_confirmation_token()
            send_email(user.email, 'Confirm Your Account',
                       'auth/email/confirm', user=user, token=token)
            email_sent = True
        except Exception as e:
            # For testing confirmation emails, don't auto-confirm
            current_app.logger.error(f'Failed to send confirmation email: {e}')

        # Show success page with login link
        return render_template('auth/register_success_simple.html',
                             user_email=user.email,
                             email_sent=email_sent)

    return render_template('auth/register.html', form=form)

@auth.route('/register-success')
def register_success():
    """Show registration success page for AJAX registrations"""
    email = request.args.get('email', '')
    email_sent = request.args.get('email_sent', 'false').lower() == 'true'
    confirmed = request.args.get('confirmed', 'false').lower() == 'true'

    if not email:
        return redirect(url_for('auth.register'))

    return render_template('auth/register_success_simple.html',
                         user_email=email,
                         email_sent=email_sent,
                         confirmed=confirmed)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('wiki.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'danger')
    return redirect(url_for('wiki.index'))

# Add template filter for date formatting
@auth.app_template_filter('moment')
def moment_filter(date):
    """Simple moment.js-like filter for date formatting"""
    if not date:
        return ''
    return date.strftime('%Y-%m-%d %H:%M:%S')

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.', 'info')
    return redirect(url_for('wiki.index'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('wiki.index'))
        else:
            flash('Invalid password.', 'danger')
    return render_template("auth/change_password.html", form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('wiki.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            try:
                token = user.generate_reset_token()
                send_email(user.email, 'Reset Your Password',
                           'auth/email/reset_password',
                           user=user, token=token)
                flash('An email with instructions to reset your password has been '
                      'sent to you.', 'info')
            except Exception as e:
                current_app.logger.error(f'Failed to send password reset email: {e}')
                flash('We encountered an issue sending the reset email. Please try again later.', 'warning')
        else:
            # Don't reveal that the email doesn't exist for security reasons
            # But log it for monitoring
            current_app.logger.info(f'Password reset requested for non-existent email: {form.email.data}')
            flash('An email with instructions to reset your password has been '
                  'sent to you.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_ajax.html', form=form)

@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('wiki.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        # Find user by token
        from itsdangerous import URLSafeTimedSerializer as Serializer
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='reset', max_age=3600)
            user_id = data.get('reset')
            user = User.query.get(user_id)
            if user and user.reset_password(token, form.password.data):
                db.session.commit()
                flash('Your password has been reset.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('The password reset link is invalid or has expired.', 'danger')
                return redirect(url_for('auth.login'))
        except:
            flash('The password reset link is invalid or has expired.', 'danger')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.', 'info')
            return redirect(url_for('wiki.index'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template("auth/change_email.html", form=form)

@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('Your email address has been updated.', 'success')
    else:
        flash('Invalid request.', 'danger')
    return redirect(url_for('wiki.index'))

@auth.route('/sessions')
@login_required
def sessions():
    """Show active user sessions"""
    sessions = UserSession.query.filter_by(user_id=current_user.id, is_active=True)\
                               .order_by(UserSession.created_at.desc()).all()
    return render_template('auth/sessions.html', sessions=sessions)

@auth.route('/revoke_session/<int:session_id>')
@login_required
def revoke_session(session_id):
    """Revoke a specific session"""
    session = UserSession.query.get_or_404(session_id)
    if session.user_id != current_user.id and not current_user.is_administrator():
        flash('You can only revoke your own sessions.', 'danger')
        return redirect(url_for('auth.sessions'))

    session.revoke()
    db.session.commit()
    flash('Session has been revoked.', 'info')
    return redirect(url_for('auth.sessions'))

@auth.route('/revoke_all_sessions')
@login_required
def revoke_all_sessions():
    """Revoke all sessions except current one"""
    current_session_token = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
    UserSession.query.filter_by(user_id=current_user.id, is_active=True)\
                    .filter(UserSession.session_token != current_session_token)\
                    .update({'is_active': False})
    db.session.commit()
    flash('All other sessions have been revoked.', 'info')
    return redirect(url_for('auth.sessions'))