from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from .forms import *
from Skill_Tracker.models import *
from django.contrib.auth.decorators import login_required

from .models import *


# Create your views here.
def register(request):
    if request.method =='POST':
        user_form =UserRegistrationForm(request.POST)
        profile_form = SkillProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Save User
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])
            user.save()
            
           
            skill_profile = profile_form.save(commit=False)
            skill_profile.user = user
            skill_profile.save()
            return redirect('login_view')  # Redirect to a home page or dashboard after registration
    else:
        user_form = UserRegistrationForm()
        profile_form = SkillProfileForm()
            
    return render(request, 'accounts/register.html',{
        'user_form': user_form,
        'profile_form': profile_form
    })
    
    
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('user_index')  # Use URL name, not template path
        else:
            error_message = "Invalid username or password."
            return render(request, 'accounts/login.html', {'error_message': error_message})
    else:
        # Handle GET request
        return render(request, 'accounts/login.html')
    
def logout_view(request):
    logout(request)
    return redirect('index')


def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/reset_password.html')
        elif new_password == request.POST.get('current_password'):
            messages.error(request, "New password must be different from current password.")
            return render(request, 'accounts/reset_password.html')
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)  # securely sets new password
            user.save()
            messages.success(request, "Password reset successfully. You can now log in.")
            return redirect('login_view')  # redirect to your login page
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
            return render(request, 'accounts/reset_password.html')

    # Handle GET request
    return render(request, 'accounts/reset_password.html')

@login_required
def profile(request):
    # Get or create the user's profile
    skill_profile, created = SkillProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': '',
            'experience_level': 'Beginner',
            'education': ''
        }
    )
    
    # Get user's goals
    goals = SkillGoal.objects.filter(user=request.user)
    completed_goals = goals.filter(is_completed=True).count()
    
    if request.method == 'POST':
        profile_form = SkillProfileForm(
            request.POST,
            instance=skill_profile  # This now always exists
        )
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        profile_form = SkillProfileForm(instance=skill_profile)
    
    context = {
        'profile_form': profile_form,
        'profile': skill_profile,
        'goals': goals,
        'completed_goals': completed_goals,
    }
    return render(request, 'accounts/profile.html', context)