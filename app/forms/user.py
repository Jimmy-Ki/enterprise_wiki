from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional

class ProfileForm(FlaskForm):
    """用户资料编辑表单"""
    name = StringField('姓名', validators=[
        Optional(),
        Length(min=1, max=64, message='姓名长度必须在1到64个字符之间')
    ])

    email = EmailField('邮箱', validators=[
        DataRequired(message='邮箱为必填项'),
        Email(message='请输入有效的邮箱地址'),
        Length(max=120, message='邮箱长度不能超过120个字符')
    ])

class NotificationSettingsForm(FlaskForm):
    """通知设置表单"""
    email_notifications = BooleanField('邮件通知', default=True)
    watch_notifications = BooleanField('关注通知', default=True)
    mention_notifications = BooleanField('提及通知', default=True)
    comment_notifications = BooleanField('评论通知', default=True)
    daily_digest = BooleanField('每日摘要', default=False)