"""Two-Factor Authentication forms"""

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.models import User


class TwoFactorSetupForm(FlaskForm):
    """双因素认证设置表单"""
    verification_code = StringField('验证码', validators=[DataRequired(), Length(6, 6)])

    # 移除表单级别的验证，在路由中处理验证逻辑


class TwoFactorVerifyForm(FlaskForm):
    """双因素认证验证表单"""
    code = StringField('认证码', validators=[DataRequired(), Length(6, 6)])
    remember_me = BooleanField('记住设备')

    # 移除表单级别的验证，在路由中处理验证逻辑


class TwoFactorDisableForm(FlaskForm):
    """禁用双因素认证表单"""
    password = PasswordField('密码', validators=[DataRequired()])
    verification_code = StringField('验证码', validators=[DataRequired(), Length(6, 6)])

    def validate_password(self, field):
        """验证密码"""
        if not current_user.verify_password(field.data):
            raise ValidationError('密码错误')

    def validate_verification_code(self, field):
        """验证TOTP码"""
        from flask_login import current_user
        if not current_user.verify_totp_token(field.data):
            raise ValidationError('验证码无效，请重试')


class TwoFactorBackupCodeForm(FlaskForm):
    """备用码登录表单"""
    backup_code = StringField('备用码', validators=[DataRequired()])

    # 移除表单级别的验证，在路由中处理验证逻辑