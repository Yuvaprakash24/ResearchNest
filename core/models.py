import re
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(upload_to='profile_pics', blank=True, null=True)
    FIELD_OF_STUDY_CHOICES = [
        ('biology', 'Biology'),
        ('chemistry', 'Chemistry'),
        ('physics', 'Physics'),
        ('computer_science', 'Computer Science'),
        ('psychology', 'Psychology'),
        ('other', 'Other'),
    ]
    field_of_study = models.CharField(max_length=100, choices=FIELD_OF_STUDY_CHOICES, blank=False)
    other_field_of_study = models.CharField(max_length=100, blank=True, null=True)  # Custom input for 'Other'

    def __str__(self):
        return self.username

class Project(models.Model):
    MODE_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('protected', 'Protected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=255)
    project_description = models.TextField()
    project_logo = models.ImageField(upload_to='project_logos', blank=True, null=True)
    project_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='public')
    protected_emails = models.TextField(blank=True, null=True)  # Comma-separated emails for protected mode
    tags = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_tags(self):
        """Returns a list of tags from the comma-separated tags field."""
        return [tag.strip() for tag in self.tags.split(',')] if self.tags else []
    
    def get_allowed_emails(self):
        if self.project_mode == 'protected':
            return self.protected_emails.split(',')  # Split by comma if multiple emails are stored
        return []

    def __str__(self):
        return self.project_name


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_files')
    file = models.FileField(upload_to='project_files')

    def clean_name(self):
            return re.sub(r'_[a-zA-Z0-9]{7}\.', '.', self.file.name.split('/')[-1])
    def __str__(self):
        return self.file.name

class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    details = models.TextField()
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    

class testimonial(models.Model):
    client_image = models.ImageField(upload_to='testimonial_imgs', null=True, blank=True)
    client_name = models.CharField(max_length=40)
    client_occupation = models.CharField(max_length=45)
    client_story = models.TextField()