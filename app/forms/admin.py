from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Optional
from wtforms.widgets import TextArea
from app.models import User

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    name = StringField('Full Name', validators=[DataRequired(), Length(1, 64)])
    password = StringField('Password', validators=[Optional()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active')
    confirmed = BooleanField('Confirmed')
    submit = SubmitField('Save User')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        from app.models import Role
        self.role_id.choices = [(r.id, r.name) for r in Role.query.all()]

class RoleForm(FlaskForm):
    name = StringField('Role Name', validators=[DataRequired(), Length(1, 64)])
    can_follow = BooleanField('Can Follow')
    can_comment = BooleanField('Can Comment')
    can_write = BooleanField('Can Write')
    can_moderate = BooleanField('Can Moderate')
    can_view_private = BooleanField('Can View Private')
    can_edit_all = BooleanField('Can Edit All')
    can_delete_all = BooleanField('Can Delete All')
    is_admin = BooleanField('Is Administrator')
    submit = SubmitField('Save Role')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])
    is_public = BooleanField('Public')
    submit = SubmitField('Save Category')