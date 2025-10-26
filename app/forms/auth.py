from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, ValidationError
from wtforms.widgets import TextArea
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('保持登录状态')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('用户名', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               '用户名只能包含字母、数字、点或下划线')])
    name = StringField('姓名', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('密码', validators=[
        DataRequired(), Length(min=8, message='密码长度至少为8个字符')])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(), EqualTo('password', message='两次输入的密码必须匹配。')])
    submit = SubmitField('注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已被注册。')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用。')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('当前密码', validators=[DataRequired()])
    password = PasswordField('新密码', validators=[
        DataRequired(), Length(min=8, message='密码长度至少为8个字符')])
    password2 = PasswordField('确认新密码', validators=[
        DataRequired(), EqualTo('password', message='两次输入的密码必须匹配。')])
    submit = SubmitField('修改密码')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('重置密码')

class PasswordResetForm(FlaskForm):
    password = PasswordField('新密码', validators=[
        DataRequired(), Length(min=8, message='密码长度至少为8个字符')])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(), EqualTo('password', message='两次输入的密码必须匹配。')])
    submit = SubmitField('重置密码')

class ChangeEmailForm(FlaskForm):
    email = StringField('新邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('更新邮箱地址')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已被注册。')

class ResendConfirmationForm(FlaskForm):
    submit = SubmitField('重新发送确认邮件', render_kw={'class': 'confluence-btn confluence-btn-primary resend-btn'})