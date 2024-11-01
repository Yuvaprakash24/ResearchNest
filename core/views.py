import urllib.request
from django.shortcuts import render,redirect, get_object_or_404
from django.db.models import Q,Count
from django.contrib import messages,auth
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from . import forms
import zipfile
import io,os
from django.http import HttpResponse,Http404,JsonResponse
from django.conf import settings
import cloudinary.uploader
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied

# Create your views here.
from . import models
def home(request):
    my_projects = {}
    public_projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        )[:3]
    testimonials = models.testimonial.objects.all()[:5]
    if(request.user.is_authenticated):
        user = request.user
    # Query to fetch projects based on visibility and user permissions
        my_projects = models.Project.objects.filter(
            Q(user=user) |  # Projects owned by the user
            (Q(project_mode='public')  & Q(user=user)) |  # Public projects
            Q(project_mode='protected', protected_emails__icontains=user.email)  # Protected projects
        )[:3]
        public_projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        ).exclude(user=user)[:3]
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
            user_email = request.user.email
            user_name = request.user
            send_mail(
                'Welcome to ResearchNest!',
                '',
                'settings.EMAIL_HOST_USER',  # From email
                [user_email],  # To email
                fail_silently=False,
                html_message=f'''
                    <h3>Hi <strong>{user_name}</strong>,</h3>
                    <br>
                    <h2>Welcome to ResearchNest!</h2>
                    <p>Thank you {user_name}, for being a part of the ResearchNest project. We're excited to have you with us!</p>
                    <br>
                    <p>Your account has been created successfully, and you can now:</p>
                    <ul>
                        <li>Manage your projects easily.</li>
                        <li>Collaborate with other researchers.</li>
                        <li>Access resources and support.</li>
                    </ul>
                    <br>
                    <p>If you have any questions, feel free to <a href="mailto:researchnest.tech@gmail.com">contact our support team</a>.</p>
                    <br>
                    <p>Best regards,</p>
                    <p>ResearchNest Team</p>
                    '''
                )
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
        # next_url = request.POST.get('next', request.GET.get('next',reverse('home')))
        next_url = request.POST.get('next') or request.GET.get('next') or reverse('home')
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


def createproject(request):
    if not request.user.is_authenticated:
        messages.warning(request,"Please LogIn first to create the project")
        return render(request, 'login.html')
    if request.method == 'POST':
        try:
            # Create project first
            project = models.Project.objects.create(
                user=request.user,
                project_name=request.POST.get('projectName'),
                project_description=request.POST.get('projectDescription'),
                project_mode=request.POST.get('projectMode'),
                protected_emails=request.POST.get('protectedEmails') if request.POST.get('projectMode') == 'protected' else '',
                tags=request.POST.get('tagsused')
            )

            # Handle project logo separately
            if 'projectLogo' in request.FILES:
                try:
                    logo_result = cloudinary.uploader.upload(
                        request.FILES['projectLogo'],
                        folder=f'project_logos/{project.id}',
                        resource_type='image'
                    )
                    project.project_logo = logo_result['secure_url']
                    project.save()
                except Exception as e:
                    messages.error(request, f'Error uploading logo: {str(e)}')

            # Handle multiple file uploads
            files = request.FILES.getlist('files[]')
            upload_errors = []
            
            for file in files:
                success, error = handle_file_upload(file, project)
                if not success:
                    upload_errors.append(f"Error uploading {file.name}: {error}")
            
            all_files = models.ProjectFile.objects.filter(project=project)
            seen_filenames = set()
            for project_file in all_files:
                if project_file.original_filename in seen_filenames:
                    project_file.delete()  # Remove duplicate
                else:
                    seen_filenames.add(project_file.original_filename)

            if upload_errors:
                messages.warning(request, "Some files failed to upload: " + "; ".join(upload_errors))
            else:
                messages.success(request, 'Project created successfully!')
                user_email = request.user.email
                user_name = request.user
                project_name = project.project_name
                send_mail(
                    'Project Created Successfully on ResearchNest!',
                    '',
                    'settings.EMAIL_HOST_USER',  # From email
                    [user_email],  # To email
                    fail_silently=False,
                    html_message=f'''
                        <h3>Hi <strong>{user_name}</strong>,</h3><br>
                        <h2>Project Created Successfully!</h2>
                        <p>Your project <strong>"{project_name}"</strong> has been created successfully.</p>
                        <p>Thank you <strong>{user_name}</strong>, for being a part of the ResearchNest project.</p>
                        <br>
                        <p>Best regards,</p>
                        <p>ResearchNest Team</p>
                        '''
                )
            return redirect('seeproject', project_id=project.id)

        except Exception as e:
            messages.error(request, f'Error creating project: {str(e)}')
            return render(request, 'create_project.html')

    return render(request, 'create_project.html')


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)

    # Check permissions based on project mode
    if project.project_mode == 'private' and project.user != request.user:
        return render(request, '404.html')  # Render a "Permission Denied" page
    
    if project.project_mode == 'protected' and request.user.email not in project.get_allowed_emails():
        return render(request, '404.html')  # Render a "Permission Denied" page

    return render(request, 'project_detail.html', {'project': project})


def allpublicprojects(request):
    projects = models.Project.objects.filter(
            Q(project_mode='public')   # Public projects
        )
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
            messages.success(request, "Project Planner item added successfully!")
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

def howcreateproject(request):
    return render(request,'howtocreateproject.html')

def aboutus(request):
    return render(request,'aboutus.html')

def contactus(request):
    if request.method == 'POST':
        form = forms.ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            messages.success(request, "Your message has been sent successfully!")
            send_mail(
                subject=f"New Contact Form Submission: {contact.subject}",
                message=(
                    f"Name: {contact.full_name}\n"
                    f"Email: {contact.email}\n"
                    f"Category: {contact.get_category_display()}\n"
                    f"Message:\n{contact.message}"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER,request.user.email],  # Add your email to receive notifications
                fail_silently=False,
            )
        else:
            messages.error(request, "There was an error with your submission. Please try again.")
    else:
        form = forms.ContactForm()
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


def seeproject(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    project_files = project.project_files.all()
    
    # Define file extensions for each category
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
    document_extensions = {'.pdf', '.doc', '.docx', '.ppt', '.pptx'}
    spreadsheet_extensions = {'.xlsx', '.xls', '.csv', '.ods'}
    text_extensions = {'.txt', '.md', '.rtf'}
    
    # Initialize categories
    categorized_files = {
        'images': [],
        'documents': [],
        'spreadsheets': [],
        'text_files': [],
        'others': []
    }
    
    # Categorize files
    for file in project_files:
        file_info = {
            'id': file.id,
            'name': file.original_filename,
            'url': file.get_file_url(),
            'uploaded_at': file.uploaded_at,
        }
        
        # Get file extension (lowercase for consistent comparison)
        _, ext = os.path.splitext(file.original_filename.lower())
        
        # Categorize based on extension
        if ext in image_extensions:
            categorized_files['images'].append(file_info)
        elif ext in document_extensions:
            categorized_files['documents'].append(file_info)
        elif ext in spreadsheet_extensions:
            categorized_files['spreadsheets'].append(file_info)
        elif ext in text_extensions:
            categorized_files['text_files'].append(file_info)
        else:
            categorized_files['others'].append(file_info)
    
    context = {
        'project': project,
        'categorized_files': categorized_files,
    }
    return render(request, 'seeproject.html', context)


@login_required
def download_project_files(request, project_id):
    try:
        # Get the project and check permissions
        project = get_object_or_404(models.Project, id=project_id)

        # Security checks
        if project.project_mode == 'private' and project.user != request.user:
            raise PermissionDenied("You don't have permission to access this project.")

        if project.project_mode == 'protected' and request.user.email not in project.get_allowed_emails():
            raise PermissionDenied("You don't have permission to access this project.")

        # Create a zip file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for project_file in project.project_files.all():
                try:
                    # Get the correct download URL based on file type
                    download_url = project_file.get_file_url()
                    
                    if not download_url:
                        print(f"Skipping {project_file.original_filename}: No valid URL")
                        continue

                    # Download the file content using urllib
                    with urllib.request.urlopen(download_url) as response:
                        file_content = response.read()
                        # Add file to zip with original filename
                        zip_file.writestr(project_file.original_filename, file_content)

                except urllib.error.URLError as e:
                    print(f"Failed to download {project_file.original_filename}: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Error processing {project_file.original_filename}: {str(e)}")
                    continue

        # Prepare the response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')

        # Create a safe project name for the zip file
        safe_project_name = "".join(x for x in project.project_name if x.isalnum() or x in (' ', '-', '_'))
        zip_filename = f'{safe_project_name}_files.zip'

        # Add headers for download
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = len(zip_buffer.getvalue())

        return response

    except models.Project.DoesNotExist:
        raise Http404("Project not found")
    except PermissionDenied as e:
        return HttpResponse(str(e), status=403)
    except Exception as e:
        print(f"Download error: {str(e)}")  # Log the error
        return HttpResponse(f"An error occurred while preparing the download: {str(e)}", status=500)


@login_required
def delete_project(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    
    # Ensure only the owner of the project can delete it
    if project.user != request.user:
        return render(request, '404.html')  # Render a "Permission Denied" page

    # Delete project files
    project_files = project.project_files.all()
    for project_file in project_files:
        # Cloudinary will automatically handle file deletion when the model is deleted
        project_file.delete()

    # Delete the project logo if it exists
    if project.project_logo:
        # Cloudinary will automatically handle file deletion when the model is deleted
        project.project_logo = None
        project.save()

    # Delete the project itself
    project.delete()

    messages.success(request, 'Project and associated files deleted successfully.')
    user_email = request.user.email
    user_name = request.user
    project_name = project.project_name
    send_mail(
        'Project Deleted Successfully on ResearchNest!',
        '',
        'settings.EMAIL_HOST_USER',  # From email
        [user_email],  # To email
        fail_silently=False,
        html_message=f'''
        <h3>Hi <strong>{user_name}</strong>,</h3><br>
        <h2>Project Deleted Successfully!</h2>
        <p>Your project <strong>"{project_name}"</strong> has been deleted successfully.</p>
        <p>Thank you <strong>{user_name}</strong>, for being a part of the ResearchNest project.</p>
        <br>
        <p>Best regards,</p>
        <p>ResearchNest Team</p>
        '''
    )
    return redirect('allprojects')

@login_required
def editproject(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    if project.user != request.user:
        if request.user.email not in project.get_allowed_emails():
            return render(request, '404.html')

    if request.method == 'POST':
        try:
            # Update project details
            project.project_name = request.POST.get('projectName')
            project.project_description = request.POST.get('projectDescription')
            project.project_mode = request.POST.get('projectMode')
            project.protected_emails = request.POST.get('protectedEmails') if request.POST.get('projectMode') == 'protected' else ''
            project.tags = request.POST.get('tagsused')

            # Handle project logo update
            if 'projectLogo' in request.FILES:
                try:
                    logo_result = cloudinary.uploader.upload(
                        request.FILES['projectLogo'],
                        folder=f'project_logos/{project.id}',
                        resource_type='image'
                    )
                    project.project_logo = logo_result['secure_url']
                except Exception as e:
                    messages.error(request, f'Error uploading logo: {str(e)}')

            project.save()

            # Handle new file uploads
            files = request.FILES.getlist('files[]')
            upload_errors = []
            
            for file in files:
                success, error = handle_file_upload(file, project)
                if not success:
                    upload_errors.append(f"Error uploading {file.name}: {error}")

            all_files = models.ProjectFile.objects.filter(project=project)
            seen_filenames = set()
            for project_file in all_files:
                if project_file.original_filename in seen_filenames:
                    project_file.delete()  # Remove duplicate
                else:
                    seen_filenames.add(project_file.original_filename)
            
            if upload_errors:
                messages.warning(request, "Some files failed to upload: " + "; ".join(upload_errors))
            else:
                messages.success(request, 'Project updated successfully!')
                user_email = request.user.email
                user_name = request.user
                project_name = project.project_name
                send_mail(
                    'Project Edited Successfully on ResearchNest!',
                    '',
                    'settings.EMAIL_HOST_USER',  # From email
                    [user_email],  # To email
                    fail_silently=False,
                    html_message=f'''
                        <h3>Hi <strong>{user_name}</strong>,</h3><br>
                        <h2>Project Edited Successfully!</h2>
                        <p>Your project <strong>"{project_name}"</strong> has been edited successfully.</p>
                        <p>Thank you <strong>{user_name}</strong>, for being a part of the ResearchNest project.</p>
                        <br>
                        <p>Best regards,</p>
                        <p>ResearchNest Team</p>
                        '''
                )
                if project.project_mode == 'protected':
                    protected_emails = project.get_allowed_emails()
                    if user_email in protected_emails:
                        protected_emails.remove(user_email)
                        protected_emails.append(project.user.email)
                    for email in protected_emails:
                        send_mail(
                            'Project Edited in Protected Mode on ResearchNest!',
                            '',
                            'settings.EMAIL_HOST_USER',  # From email
                            [email],  # To email
                            fail_silently=False,
                            html_message=f'''
                                <h3>Hi,</h3><br>
                                <h2>Project Edited Successfully!</h2>
                                <p>The project <strong>"{project_name}"</strong> has been edited by <strong>{user_name}</strong>.</p>
                                <p>Best regards,</p>
                                <p>ResearchNest Team</p>
                            '''
                        )

            return redirect('seeproject', project_id=project.id)

        except Exception as e:
            messages.error(request, f'Error updating project: {str(e)}')
            return render(request, 'create_project.html', {'project': project})

    return render(request, 'create_project.html', {'project': project})


@login_required
def delete_file(request, file_id):
    file = get_object_or_404(models.ProjectFile, id=file_id)
    project_id = file.project.id
    # Cloudinary will automatically handle file deletion
    file.delete()
    messages.success(request, 'File deleted successfully.')
    return redirect('editproject', project_id)


def handle_file_upload(file, project):
    try:
        # Determine if it's an image based on file extension
        _, ext = os.path.splitext(file.name.lower())
        is_image = ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
        
        # Upload with appropriate resource type
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f'project_files/{project.id}',
            resource_type='image' if is_image else 'raw',
            use_filename=True,
            unique_filename=True
        )
        
        # Create ProjectFile instance
        project_file = models.ProjectFile.objects.create(
            project=project,
            file=upload_result['public_id'],
            original_filename=file.name
        )
        
        return True, None
    except Exception as e:
        return False, str(e)