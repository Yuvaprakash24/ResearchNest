import os
import cloudinary
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from cloudinary.models import CloudinaryField
from urllib.parse import urlparse

class User(AbstractUser):
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(unique=True)
    profile_picture = CloudinaryField(folder='profile_pics', blank=True, null=True)
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
    project_logo = CloudinaryField(folder='project_logos', blank=True, null=True)
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
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('spreadsheet', 'Spreadsheet'),
        ('text', 'Text'),
        ('other', 'Other')
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_files')
    file = CloudinaryField('File', folder='project_files', resource_type='auto')  # Changed to auto
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def determine_file_type(self):
        ext = os.path.splitext(self.original_filename.lower())[1]
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}:
            return 'image'
        elif ext in {'.pdf', '.doc', '.docx'}:
            return 'document'
        elif ext in {'.xlsx', '.xls', '.csv', '.ods'}:
            return 'spreadsheet'
        elif ext in {'.txt', '.md', '.rtf'}:
            return 'text'
        return 'other'

    def save(self, *args, **kwargs):
        if not self.file_type or self.file_type == 'other':
            self.file_type = self.determine_file_type()
        super().save(*args, **kwargs)

    def clean_name(self):
        return self.original_filename
    
    def get_file_url(self):
        if not self.file:
            return None
            
        try:
            # For PDFs, documents, and other non-image files
            if self.file_type in ['document', 'spreadsheet', 'text', 'other']:
                url = cloudinary.utils.cloudinary_url(
                    self.file.public_id,
                    resource_type='raw',  # Changed from 'auto' to 'raw'
                    format=os.path.splitext(self.original_filename)[1][1:] if self.original_filename else None
                )[0]
            # For images
            elif self.file_type == 'image':
                url = cloudinary.utils.cloudinary_url(
                    self.file.public_id,
                    resource_type='image'
                )[0]
            
            return url
        except Exception as e:
            print(f"Error generating URL for {self.original_filename}: {str(e)}")
            return None
    def __str__(self):
        return f"{self.original_filename} ({self.file_type})"

class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    details = models.TextField()
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    

class testimonial(models.Model):
    client_image = CloudinaryField(folder='testimonial_imgs', null=True, blank=True)
    client_name = models.CharField(max_length=40)
    client_occupation = models.CharField(max_length=45)
    client_story = models.TextField()


class Contact(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Support'),
        ('feedback', 'Feedback'),
    ]

    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name}"