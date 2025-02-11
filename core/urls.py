from django.urls import path
from . import views
urlpatterns = [
    path('', views.home,name="home"),
    path('signup',views.signup,name="signup"),
    path('login',views.login,name="login"),
    path('logout/', views.logout, name='logout'),
    path('createproject',views.createproject,name="createproject"),
    path('tags',views.tags,name="tags"),
    path('profile',views.profile,name="profile"),
    path('todolist',views.todolist,name="todolist"),
    path('del/<str:item_id>', views.remove, name="del"),
    path('whyresearchnest',views.whyresearchnest,name="whyresearchnest"),
    path('aboutus',views.aboutus,name="aboutus"),
    path('contactus',views.contactus,name="contactus"),
    path('clientstories',views.clientstories,name="clientstories"),
    path('editprofile', views.editprofile, name='editprofile'),
    path('allpublicprojects',views.allpublicprojects,name="allpublicprojects"),
    path('allprojects',views.allprojects,name="allprojects"),
    path('userpublicprojects',views.userpublicprojects,name="userpublicprojects"),
    path('userprotectedprojects',views.userprotectedprojects,name="userprotectedprojects"),
    path('userprivateprojects',views.userprivateprojects,name="userprivateprojects"),
    path('seeproject/<int:project_id>/',views.seeproject,name="seeproject"),
    path('seeproject/<int:project_id>/download/', views.download_project_files, name='download_project_files'),
    path('seeproject/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('seeproject/<int:project_id>/edit-project/', views.editproject, name='editproject'),
    path('delete-file/<int:file_id>/', views.delete_file, name='delete_file'),
    path('tags/', views.search_tags, name='search_tags'),
    path('tags/filter', views.filter_tags, name='filter_tags'),
    path('search/', views.search_view, name='search'),
    path('howcreateproject/', views.howcreateproject, name='howcreateproject'),
    path('categories/', views.category_page, name='category_page'),
]