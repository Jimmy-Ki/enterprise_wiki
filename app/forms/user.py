from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional

class ProfileForm(FlaskForm):
    """用户资料编辑表单"""
    name = StringField('Name', validators=[
        Optional(),
        Length(min=1, max=64, message='Name must be between 1 and 64 characters')
    ])

    email = EmailField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=120, message='Email must be less than 120 characters')
    ])

class NotificationSettingsForm(FlaskForm):
    """通知设置表单"""
    email_notifications = BooleanField('Email Notifications', default=True)
    watch_notifications = BooleanField('Watch Notifications', default=True)
    mention_notifications = BooleanField('Mention Notifications', default=True)
    comment_notifications = BooleanField('Comment Notifications', default=True)
    daily_digest = BooleanField('Daily Digest', default=False)