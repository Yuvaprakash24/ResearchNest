from django import forms
from .models import User,Todo
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'field_of_study', 'other_field_of_study', 'password1', 'password2']

    def clean(self):
        cleaned_data = super().clean()
        field_of_study = cleaned_data.get('field_of_study')
        other_field_of_study = cleaned_data.get('other_field_of_study')

        # Ensure that if "Other" is selected, the user must provide additional input
        if field_of_study == 'other' and not other_field_of_study:
            self.add_error('other_field_of_study', 'Please specify your field of study.')

class EditProfileForm(UserChangeForm):
    password = None  # Exclude the password field from the form
    email = None 
    remove_profile_picture = forms.BooleanField(required=False, label="Remove profile picture")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'profile_picture', 'field_of_study', 'other_field_of_study']  # Include 'other_field_of_study'

    def clean(self):
        cleaned_data = super().clean()
        field_of_study = cleaned_data.get('field_of_study')
        other_field_of_study = cleaned_data.get('other_field_of_study')

        # Ensure that if "Other" is selected, the user must provide additional input
        if field_of_study == 'other' and not other_field_of_study:
            self.add_error('other_field_of_study', 'Please specify your field of study.')
        
        return cleaned_data
    
class TodoForm(forms.ModelForm):
    class Meta:
        model = Todo
        exclude = ['user']