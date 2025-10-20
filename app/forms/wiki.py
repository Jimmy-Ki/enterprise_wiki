from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, FileField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from wtforms.widgets import TextArea
from app.models import Category, Page

class PageForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 128)])
    content = TextAreaField('Content', validators=[DataRequired()],
                           widget=TextArea(),
                           render_kw={'rows': 20, 'class': 'form-control markdown-editor'})
    summary = StringField('Summary', validators=[Optional(), Length(max=500)],
                         description='Brief description of the page (optional)')
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    change_summary = StringField('Change Summary', validators=[Optional(), Length(max=255)],
                                description='Describe what you changed in this edit')
    is_published = BooleanField('Published', default=True,
                               description='Make this page visible to others')
    is_public = BooleanField('Public', default=True,
                            description='Allow anyone to view this page')
    submit = SubmitField('Save Page')

    def __init__(self, *args, **kwargs):
        super(PageForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'No Category')] + [(c.id, c.name) for c in Category.query.all()]

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('Description', validators=[Optional()])
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])
    is_public = BooleanField('Public', default=True)
    submit = SubmitField('Save Category')

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in Category.query.all()]

class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])

class AttachmentForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    is_public = BooleanField('Public', default=True)
    submit = SubmitField('Upload File')