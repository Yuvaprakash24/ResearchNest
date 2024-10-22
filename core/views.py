import os
import re
from django.shortcuts import render,redirect, get_object_or_404
from django.db.models import Q,Count
from django.contrib import messages,auth
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from . import forms
import zipfile
import io
from django.http import HttpResponse
from django.conf import settings

# Create your views here.
from . import models
def home(request):
    my_projects = {}
    public_projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        )[:6]
    testimonials = models.testimonial.objects.all()[:5]
    if(request.user.is_authenticated):
        user = request.user
    # Query to fetch projects based on visibility and user permissions
        my_projects = models.Project.objects.filter(
            Q(user=user) |  # Projects owned by the user
            (Q(project_mode='public')  & Q(user=user)) |  # Public projects
            Q(project_mode='protected', protected_emails__icontains=user.email)  # Protected projects
        )[:6]
        public_projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        ).exclude(user=user)[:6]
    return render(request, 'index.html', {'my_projects': my_projects,'public_projects': public_projects,'testimonials': testimonials})

def search_view(request):
    query = request.GET.get('q')  # Get the search query from the URL
    results = []

    if query:
        results = models.Project.objects.filter(
            Q(project_name__icontains=query) | Q(project_description__icontains=query) | Q(tags__icontains=query)
        )
    context = {
        'query': query,
        'projects': results,
    }
    return render(request, 'search.html', context)

def signup(request):
    if request.method == 'POST':
        form = forms.SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            user.save()
            auth_login(request, user)  # Log the user in after registration
            return redirect('home')  # Redirect to 'home' after successful signup
    else:
        form = forms.SignUpForm()

    return render(request, 'signup.html', {'form': form})

def logout(request):
    auth.logout(request)
    return redirect("/")

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', request.GET.get('next',reverse('home')))
        print(f"Next URL: {next_url}")
        user = authenticate(username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect(next_url)
        else:
            messages.warning(request, "Invalid Credentials")
            return redirect(reverse('login') + f'?next={next_url}')
    else:
        next_url = request.GET.get('next', reverse('home'))
        return render(request, "login.html", {'next': next_url})

@login_required
def createproject(request):
    if request.method == 'POST':
        # Process the form input
        messages.success(request, 'Project created successfully!')
        project_name = request.POST.get('projectName')
        project_description = request.POST.get('projectDescription')
        project_logo = request.FILES.get('projectLogo')
        project_mode = request.POST.get('projectMode')
        protected_emails = request.POST.get('protectedEmails') if project_mode == 'protected' else ''
        tags = request.POST.get('tagsused')
        files = request.FILES.getlist('files[]')
        # Create the project instance and link it to the logged-in user
        project = models.Project.objects.create(
            user=request.user,
            project_name=project_name,
            project_description=project_description,
            project_logo=project_logo,
            project_mode=project_mode,
            protected_emails=protected_emails,
            tags=tags,
        )

        # Handle file uploads and remove duplicates
        def clean_filename(file_name):
            # Use regex to remove Django's appended identifier (e.g., '_CG31PYu')
            return re.sub(r'_[a-zA-Z0-9]{7}\.', '.', file_name)  # Matches 7-character suffix before the file extension

        seen_files = set()
        for file in files:
            clean_file_name = clean_filename(file.name)
            if clean_file_name not in seen_files:
                # Save the unique file
                models.ProjectFile.objects.create(project=project, file=file)
                seen_files.add(clean_file_name)

        # Now check for and delete any duplicate files that may exist in the project
        project_files = project.project_files.all()

        for file_obj in project_files:
            cleaned_file_name = clean_filename(file_obj.file.name)
            if cleaned_file_name in seen_files:
                # If a duplicate file is found, delete the file
                file_obj.delete()

    return render(request, 'create_project.html')





@login_required
def project_detail(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)

    # Check permissions based on project mode
    if project.project_mode == 'private' and project.user != request.user:
        return render(request, '403.html')  # Render a "Permission Denied" page
    
    if project.project_mode == 'protected' and request.user.email not in project.get_allowed_emails():
        return render(request, '403.html')  # Render a "Permission Denied" page

    return render(request, 'project_detail.html', {'project': project})


def allpublicprojects(request):
    projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        )
    if (request.user.is_authenticated):
        user = request.user

        # Query to fetch projects based on visibility and user permissions
        projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        ).exclude(user=user)

    return render(request, 'allprojects.html', {'projects': projects, 'heading': 'Public'})

@login_required
def allprojects(request):
    user = request.user

    # Query to fetch projects based on visibility and user permissions
    projects = models.Project.objects.filter(
        Q(user=user) |  # Projects owned by the user
        (Q(project_mode='public')  & Q(user=user)) |  # Public projects
        Q(project_mode='protected', protected_emails__icontains=user.email)  # Protected projects
    ).distinct()

    return render(request, 'allprojects.html', {'projects': projects, 'heading': 'My'})

@login_required
def userpublicprojects(request):
    user = request.user

    # Query to fetch projects based on visibility and user permissions
    projects = models.Project.objects.filter(
        (Q(project_mode='public')  & Q(user=user))   # Public projects
    ).distinct()

    return render(request, 'allprojects.html', {'projects': projects , 'heading': 'My Public'})

@login_required
def userprotectedprojects(request):
    user = request.user

    # Query to fetch projects based on visibility and user permissions
    projects = models.Project.objects.filter(
        Q(project_mode='protected') & (Q(user=user) | Q(protected_emails__icontains=user.email))
    ).distinct()

    return render(request, 'allprojects.html', {'projects': projects , 'heading': 'My Protected'})

@login_required
def userprivateprojects(request):
    user = request.user

    # Query to fetch projects based on visibility and user permissions
    projects = models.Project.objects.filter(
        (Q(project_mode='private')  & Q(user=user))   # Public projects
    ).distinct()

    return render(request, 'allprojects.html', {'projects': projects , 'heading': 'My Private'})


def tags(request):
    projects = models.Project.objects.filter(project_mode='public').order_by('project_name')
    return render(request,'tags.html',{'projects': projects})

def search_tags(request):
    query = request.GET.get('query')
    if query:
        projects = models.Project.objects.filter(tags__icontains=query, project_mode='public')
    else:
        projects = models.Project.objects.filter(project_mode='public')
    return render(request, 'tags.html', {'projects': projects , 'query':query})

from django.http import JsonResponse

def filter_tags(request):
    filter_type = request.GET.get('type')

    if filter_type == 'tag_count':
        projects = models.Project.objects.filter(project_mode='public')
        projects = sorted(projects, key=lambda p: len(p.get_tags()), reverse=True)
    elif filter_type == 'name':
        projects = models.Project.objects.filter(project_mode='public').order_by('project_name')
    elif filter_type == 'new':
        projects = models.Project.objects.filter(project_mode='public').order_by('-created_at')
    else:
        projects = models.Project.objects.filter(project_mode='public')

    # Create a list of project data to return as JSON
    project_data = []
    for project in projects:
        project_data.append({
            'id': project.id,  # Add project ID for linking to details page
            'project_name': project.project_name,
            'tags': project.get_tags(),  # Ensure we send parsed tags list
            'created_at': project.created_at.strftime('%Y-%m-%d'),  # Format date
            'project_description': project.project_description[:100],  # limit description length
            'user': project.user.username  # Add the project owner's name
        })

    return JsonResponse({'projects': project_data})


@login_required
def profile(request):
    user=request.user
    name=user
    email=user.email
    lname=user.last_name
    fname=user.first_name
    profile_picture = user.profile_picture.url if user.profile_picture else None
    field_study=user.other_field_of_study if user.field_of_study == 'other' else user.field_of_study
    return render(request,'profile.html',{'name':name,'email':email,'field_study':field_study,'lname':lname,'fname':fname, 'profile_picture':profile_picture})

@login_required
def todolist(request):
    item_list = models.Todo.objects.filter(user=request.user).order_by("date")
    if request.method == "POST":
        form = forms.TodoForm(request.POST)
        if form.is_valid():
            todo_item = form.save(commit=False)
            todo_item.user = request.user
            todo_item.save()
            messages.success(request, "Todo item added successfully!")
            return redirect('todolist')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}",extra_tags='danger')
    form = forms.TodoForm()

    page = {
        "forms": form,
        "list": item_list,
    }
    return render(request, 'todo.html', page)

@login_required
def remove(request, item_id):
    item = models.Todo.objects.get(id=item_id, user=request.user)
    if item:
        item.delete()
        messages.info(request, "Item removed!")
    else:
        messages.error(request, "You do not have permission to delete this item.")
    return redirect('todolist')


def whyresearchnest(request):
    return render(request,'whyresearchnest.html')

def aboutus(request):
    return render(request,'aboutus.html')

def contactus(request):
    return render(request,'contactus.html')

def clientstories(request):
    testimonials = models.testimonial.objects.all()
    return render(request,'clientstories.html',{'testimonials':testimonials})

@login_required
def editprofile(request):
    if request.method == 'POST':
        form = forms.EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Check if the user has requested to remove the profile picture
            if form.cleaned_data.get('remove_profile_picture'):
                user.profile_picture.delete(save=False)  # This will remove the file from storage
                user.profile_picture = None  # Set the field to null in the database
            
            user.save()
            return redirect('profile')
    else:
        form = forms.EditProfileForm(instance=request.user)
    return render(request, 'editprofile.html', {'form': form})


# def seeproject(request, project_id):
#     project = get_object_or_404(models.Project, id=project_id)
#     project_files = project.project_files.all()
#     context = {
#         'project': project,
#         'project_files': project_files,
#     }
#     return render(request, 'seeproject.html', context)


# def clean_filename(file_name):
#     # Use regex to remove Django's appended identifier (e.g., '_CG31PYu')
#     # Matches 7-character suffix before the file extension
#     return re.sub(r'_[a-zA-Z0-9]{7}\.', '.', file_name)

def seeproject(request, project_id):
    # Get the project and related files
    project = get_object_or_404(models.Project, id=project_id)
    project_files = project.project_files.all()  # Retrieve all related files for the project

    # Clean the filenames
    # cleaned_files = []
    # for file in project_files:
    #     cleaned_file_name = clean_filename(file.file.name).split('/')[-1]
    #     cleaned_files.append({
    #         'original': file,  # Original file object
    #         'clean_name': cleaned_file_name,  # Cleaned file name
    #     })

    context = {
        'project': project,
        'project_files': project_files,  
    }

    return render(request, 'seeproject.html', context)

@login_required
def download_project_files(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    
    # Ensure user has permission to download project files
    if project.project_mode == 'private' and project.user != request.user:
        return render(request, '403.html')  # Render a "Permission Denied" page
    
    if project.project_mode == 'protected' and request.user.email not in project.get_allowed_emails():
        return render(request, '403.html')  # Render a "Permission Denied" page

    # Collect all project files
    project_files = project.project_files.all()

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for project_file in project_files:
            file_path = project_file.file.path  # Full file path on the server
            file_name = project_file.clean_name()  # Clean filename
            zip_file.write(file_path, file_name)  # Add file to zip with clean name

    zip_buffer.seek(0)

    # Return zip file as downloadable response
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={project.project_name}_files.zip'

    return response

@login_required
def delete_project(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    
    # Ensure only the owner of the project can delete it
    if project.user != request.user:
        return render(request, '403.html')  # Render a "Permission Denied" page

    # Get all the project files and delete them from the file system
    project_files = project.project_files.all()
    for project_file in project_files:
        if os.path.exists(project_file.file.path):
            os.remove(project_file.file.path)  # Delete the file from the file system
        project_file.delete()  # Delete the file record from the database

    # Delete the project itself
    project.delete()

    messages.success(request, 'Project and associated files deleted successfully.')
    return redirect('allprojects')  # Redirect to the user's profile page or another appropriate page


@login_required
def editproject(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    if project.user != request.user and request.user.email not in project.get_allowed_emails():
        return render(request, '403.html')  # Render a "Permission Denied" page

    if request.method == 'POST':
        messages.success(request, 'Project updated successfully!')
        # Update project fields with form input
        project.project_name = request.POST.get('projectName')
        project.project_description = request.POST.get('projectDescription')
        project_mode = request.POST.get('projectMode')
        project.project_mode = project_mode
        project.protected_emails = request.POST.get('protectedEmails') if project_mode == 'protected' else ''
        project.tags = request.POST.get('tagsused')

        # Update project logo if a new one is uploaded
        if request.FILES.get('projectLogo'):
            project.project_logo = request.FILES['projectLogo']

        project.save()

        # Handle new files
        files = request.FILES.getlist('files[]')
        
        # Helper to clean duplicate file names
        def clean_filename(file_name):
            return re.sub(r'_[a-zA-Z0-9]{7}\.', '.', file_name)

        seen_files = set(file.file.name for file in project.project_files.all())

        for file in files:
            clean_file_name = clean_filename(file.name)
            if clean_file_name not in seen_files:
                models.ProjectFile.objects.create(project=project, file=file)
                seen_files.add(clean_file_name)

        return redirect('seeproject', project_id=project.id)

    return render(request, 'create_project.html', {'project': project})

@login_required
def delete_file(request, file_id):
    # file = get_object_or_404(models.ProjectFile, id=file_id, project__user=request.user)
    file = get_object_or_404(models.ProjectFile, id=file_id)
    file.delete()
    return redirect('editproject', file.project.id)