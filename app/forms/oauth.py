"""OAuth相关表单"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, URL, Email
from app.models.oauth import OAuthProvider


class OAuthProviderForm(FlaskForm):
    """OAuth提供者配置表单"""
    name = StringField('提供者名称', validators=[DataRequired(), Length(min=2, max=50)])
    display_name = StringField('显示名称', validators=[DataRequired(), Length(min=2, max=100)])
    client_id = StringField('客户端ID', validators=[DataRequired(), Length(min=1, max=200)])
    client_secret = StringField('客户端密钥', validators=[DataRequired(), Length(min=1, max=500)])
    authorize_url = StringField('授权URL', validators=[DataRequired(), URL()])
    token_url = StringField('令牌URL', validators=[DataRequired(), URL()])
    user_info_url = StringField('用户信息URL', validators=[DataRequired(), URL()])
    scope = StringField('权限范围', validators=[DataRequired()], default='openid email profile')

    # 字段映射
    user_id_field = StringField('用户ID字段', default='id')
    email_field = StringField('邮箱字段', default='email')
    name_field = StringField('姓名字段', default='name')
    username_field = StringField('用户名字段', default='login')
    avatar_field = StringField('头像字段', default='avatar_url')

    # 功能设置
    is_active = BooleanField('启用', default=True)
    auto_register = BooleanField('自动注册新用户', default=True)
    skip_2fa = BooleanField('跳过双因素认证', default=True)
    default_role = SelectField('默认角色', choices=[
        ('Viewer', '查看者'),
        ('Editor', '编辑者'),
        ('Moderator', '管理员'),
        ('Administrator', '超级管理员')
    ], default='Viewer')

    submit = SubmitField('保存配置')

    def validate_name(self, field):
        """验证提供者名称唯一性"""
        if OAuthProvider.query.filter_by(name=field.data).first():
            raise ValueError('该提供者名称已存在')