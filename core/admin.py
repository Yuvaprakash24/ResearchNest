from django.contrib import admin
from . import models
# Register your models here.
admin.site.register(models.User)
admin.site.register(models.Project)
admin.site.register(models.ProjectFile)
admin.site.register(models.Todo)
admin.site.register(models.testimonial)