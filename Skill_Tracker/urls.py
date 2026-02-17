from django.urls import path,include
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('user_index/', user_index, name='user_index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('add_skill/', add_skill, name='add_skill'),
    path('edit_skill/<int:skill_id>/', edit_skill, name='edit_skill'),
    path('delete_skill/<int:skill_id>/', delete_skill, name='delete_skill'),
    path('view_skill/<int:goal_id>/', view_skill, name='view_skill'),
    path('skill_list/', skill_list, name='skill_list'),
    path('skill_goal/', skill_goal, name='skill_goal'),
    path('view_goals/', view_goals, name='view_goals'),
    path('view_goals/<int:skill_id>/', view_goals, name='view_goals'),
    path('skill/<int:skill_id>/goal/<int:goal_id>/',view_goal_detail,name='view_goal_detail'),
    path('goal_detail/<int:goal_id>/', goal_detail, name='goal_detail'),
    path('edit_goal/<int:goal_id>/', edit_goal, name='edit_goal'),
    path('delete_goal/<int:goal_id>/', delete_goal, name='delete_goal'),
    path('skill_progress_list/', skill_progress_list, name='skill_progress_list'),
    path('add_skill_progress/<int:skill_id>/',add_skill_progress, name='add_skill_progress'),
    path('delete-progress/<int:progress_id>/',delete_skill_progress,name='delete_skill_progress'),

    path('goal/<int:goal_id>/complete/',mark_goal_completed, name='mark_goal_completed'),
    path('skill/<int:skill_id>/complete/', mark_skill_completed, name='mark_skill_completed'),
    path('progress/edit/<int:progress_id>/', edit_skill_progress, name='edit_skill_progress'),
    path('note-library/',note_library, name='note_library'),
    path('add-note/<int:skill_id>/',add_note, name='add_note'),
    path('delete-note/<int:note_id>/',delete_note, name='delete_note'),

    path('accounts/', include('accounts.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)