from datetime import date, timedelta, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum, Avg, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek
from django.http import JsonResponse
import json
from django.utils import timezone
from .models import *
from .forms import *

import plotly.graph_objs as go
import plotly.express as px
from plotly.offline import plot
from plotly.subplots import make_subplots
import numpy as np


# =====================================================
# BASIC PAGES
# =====================================================

def index(request):
    return render(request, 'user/index.html')

@login_required
def user_index(request):
    skills = Skill.objects.filter(user=request.user)

    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_skills = skills.filter(
        Q(is_active=True) | Q(last_practiced__gte=thirty_days_ago)
    ).count()
    
    completed_skills = skills.filter(is_completed=True).count()
    

    notes = NoteLibrary.objects.filter(skill__user=request.user).order_by('-uploaded_at')
    notes_count = notes.count()
    
    # Calculate streak
    streak = 0
    if skills.exists():
    
        latest_practice = skills.filter(
            last_practiced__isnull=False
        ).order_by('-last_practiced').first()
        
        if latest_practice and latest_practice.last_practiced:
            today = timezone.now().date()
            last_practice_date = latest_practice.last_practiced  # This is already a date
            
            days_since = (today - last_practice_date).days
            
            if days_since <= 1:
                streak = 7
    
    total_hours = 0
    context = {
        'skills': skills,
        'active_skills': active_skills,
        'completed_skills': completed_skills,
        'notes': notes[:4],  # Get first 4 notes for display
        'streak': streak,
        'total_hours': total_hours,
    }
    return render(request, 'user/user_index.html', context)

# =====================================================
# SKILL (MASTER DATA)
# =====================================================

@login_required
def add_skill(request):
    form = SkillForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        skill = form.save(commit=False)
        skill.user = request.user
        skill.save()
        return redirect('skill_goal')

    return render(request, 'user/add_skill.html', {'form': form})


@login_required
def delete_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)

    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill deleted successfully!")
        return redirect("user_index")

    return render(request, "user/delete_skill.html", {"skill": skill})


@login_required
def skill_list(request):
    skills = Skill.objects.filter(user=request.user)

    stats = skills.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        inactive=Count('id', filter=Q(is_active=False)),
        beginner=Count('id', filter=Q(proficiency_level='beginner')),
        intermediate=Count('id', filter=Q(proficiency_level='intermediate')),
        advanced=Count('id', filter=Q(proficiency_level='advanced')),
    )

    context = {
        'skills': skills,
        'total_skills': stats.get('total', 0),
        'active_skills': stats.get('active', 0),
        'inactive_skills': stats.get('inactive', 0),
        'beginner_count': stats.get('beginner', 0),
        'intermediate_count': stats.get('intermediate', 0),
        'advanced_count': stats.get('advanced', 0),
    }

    return render(request, 'user/skill_list.html', context)


# =====================================================
# SKILL GOALS
# =====================================================

@login_required
def skill_goal(request):
    form = SkillGoalForm(request.POST or None, request.FILES or None)
    form.fields['skill'].queryset = Skill.objects.filter(user=request.user)

    if request.method == 'POST' and form.is_valid():
        goal = form.save(commit=False)
        goal.user = request.user
        goal.save()
        return redirect('view_goal_detail', skill_id=goal.skill.id, goal_id=goal.id)

    return render(request, 'user/skill_goal.html', {'form': form})


@login_required
def view_goals(request, skill_id=None):
    if skill_id:
        skill = get_object_or_404(Skill, id=skill_id, user=request.user)
        goals = SkillGoal.objects.filter(skill=skill)
    else:
        skill = None
        goals = SkillGoal.objects.filter(skill__user=request.user)

    active_count = goals.filter(is_completed=False).count()
    completed_count = goals.filter(is_completed=True).count()

    return render(request, 'user/view_goal.html', {
        'goals': goals,
        'active_count': active_count,
        'completed_count': completed_count,
        'skill': skill,
    })


@login_required
def goal_detail(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)
    return render(request, 'user/goal_detail.html', {'goal': goal})


@login_required
def view_skill(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)
    return render(request, "user/view_skill.html", {
        'goal': goal,
        'skill': goal.skill,
    })


@login_required
def edit_skill(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    form = SkillForm(request.POST or None, instance=skill)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("view_skill", skill_id=skill.id)

    return render(request, "user/edit_skill.html", {
        "form": form,
        "skill": skill
    })


@login_required
def edit_goal(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)
    form = SkillGoalForm(request.POST or None, request.FILES or None, instance=goal)
    form.fields['skill'].queryset = Skill.objects.filter(user=request.user)

    if request.method == "POST" and form.is_valid():
        goal = form.save()

        if goal.is_completed:
            return redirect("complete_skill_decision", goal_id=goal.id)

        messages.success(request, "Skill goal updated successfully!")
        return redirect("view_goals")

    return render(request, "user/edit_goal.html", {
        "form": form,
        "goal": goal
    })


@login_required
def complete_skill_decision(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)
    skill = goal.skill

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "complete":
            skill.is_completed = True
            skill.is_active = False
            skill.save()

        elif action == "continue":
            skill.is_completed = False
            skill.is_active = True
            skill.save()

        messages.success(request, "Skill status updated successfully!")
        return redirect("dashboard")

    return render(request, "user/complete_decision.html", {
        "goal": goal,
        "skill": skill
    })


@login_required
def delete_goal(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)

    if request.method == "POST":
        goal.delete()
        messages.success(request, "Skill goal deleted successfully!")
        return redirect("view_goals")

    return render(request, "user/delete_goal.html", {"goal": goal})


@login_required
def view_goal_detail(request, skill_id, goal_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    goal = get_object_or_404(SkillGoal, id=goal_id, skill=skill)

    return render(request, "user/view_goal_detail.html", {
        "skill": skill,
        "goal": goal
    })


# =====================================================
# SKILL PROGRESS
# =====================================================

@login_required
def skill_progress_list(request):
    skills = Skill.objects.filter(user=request.user)
    notes = NoteLibrary.objects.filter(user=request.user)
    progress_list = SkillProgress.objects.filter(user=request.user)

    return render(request, 'user/skill_progress_list.html', {
        'skills': skills,
        'progress_list': progress_list,
        'notes':notes
    })


@login_required
def add_skill_progress(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)

    planned_time = 0
    goal = SkillGoal.objects.filter(
        user=request.user,
        skill=skill,
        is_completed=False
    ).order_by('-created_at').first()

    if goal:
        planned_time = goal.daily_study_hours or 0

    form = SkillProgressForm(request.POST or None, request.FILES or None, user=request.user)

    if request.method == 'POST' and form.is_valid():
        progress = form.save(commit=False)
        progress.user = request.user
        progress.skill = skill
        progress.planned_time = planned_time

        if goal and date.today() >= goal.target_date and not goal.is_completed:
            goal.is_completed = True
            goal.save()
            return redirect("complete_skill_decision", goal_id=goal.id)

        if SkillProgress.objects.filter(
            user=request.user,
            skill=skill,
            date=date.today()
        ).exists():
            messages.error(request, "You already added progress for today.")
            return redirect('skill_progress_list')

        progress.extra_time = max(progress.actual_time - planned_time, 0)

        skill.last_practiced = date.today()
        skill.save()

        progress.save()

        messages.success(request, "Skill progress added successfully!")
        return redirect('skill_progress_list')

    return render(request, 'user/add_skill_progress.html', {
        'form': form,
        'planned_time': planned_time,
        'skill': skill,
    })


@login_required
def edit_skill_progress(request, progress_id):
    progress = get_object_or_404(SkillProgress, id=progress_id, user=request.user)
    form = SkillProgressForm(request.POST or None, instance=progress)
    form.fields['skill'].queryset = Skill.objects.filter(user=request.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Skill progress updated successfully!")
        return redirect('skill_progress_list')

    return render(request, 'user/edit_skill_progress.html', {
        'form': form,
        'progress': progress
    })


@login_required
def delete_skill_progress(request, progress_id):
    progress = get_object_or_404(SkillProgress, id=progress_id, user=request.user)

    if request.method == "POST":
        progress.delete()
        messages.success(request, "Skill progress deleted successfully!")
        return redirect("skill_progress_list")

    return render(request, "user/delete_skill_progress.html", {
        "progress": progress
    })


@login_required
def add_note(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    form = NoteLibraryForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        note = form.save(commit=False)
        note.user = request.user
        note.skill = skill
        note.save()

        messages.success(request, "Note uploaded successfully!")
        return redirect("note_library")

    return render(request, "user/add_note.html", {
        "form": form,
        "skill": skill
    })


@login_required
def note_library(request):
    skills = Skill.objects.filter(user=request.user)
    notes = NoteLibrary.objects.filter(user=request.user).order_by('-uploaded_at')

    return render(request, "user/note_library.html", {
        "skills": skills,
        "notes": notes
    })


@login_required
def delete_note(request, note_id):
    note = get_object_or_404(NoteLibrary, id=note_id, user=request.user)

    if request.method == "POST":
        note.delete()
        messages.success(request, "Note deleted successfully!")
        return redirect("note_library")

    return render(request, "user/delete_note.html", {"note": note})

@login_required
def mark_goal_completed(request, goal_id):
    goal = get_object_or_404(SkillGoal, id=goal_id, user=request.user)

    if not goal.is_completed:
        goal.is_completed = True
        goal.save()  # This will auto-complete skill (because of your save override)

        messages.success(request, "Goal marked as completed 🎉")

    return redirect('goal_detail', goal.id)

@login_required
def mark_skill_completed(request, skill_id):
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)

    if not skill.is_completed:
        skill.is_completed = True
        skill.save()

    return redirect('view_skill', skill.id)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_total_study_time(user):
    return SkillProgress.objects.filter(user=user)\
        .aggregate(total=Sum('actual_time'))['total'] or 0


def get_today_progress(user):
    return SkillProgress.objects.filter(
        user=user,
        date=date.today()
    ).aggregate(total=Sum('actual_time'))['total'] or 0


def get_weekly_progress(user):
    week_ago = date.today() - timedelta(days=7)
    return SkillProgress.objects.filter(
        user=user,
        date__gte=week_ago
    ).aggregate(total=Sum('actual_time'))['total'] or 0


def get_monthly_progress(user):
    month_ago = date.today() - timedelta(days=30)
    return SkillProgress.objects.filter(
        user=user,
        date__gte=month_ago
    ).aggregate(total=Sum('actual_time'))['total'] or 0


def get_goal_stats(user):
    return {
        "total": SkillGoal.objects.filter(user=user).count(),
        "completed": SkillGoal.objects.filter(user=user, is_completed=True).count(),
        "active": SkillGoal.objects.filter(user=user, is_completed=False).count(),
    }


def get_goal_completion_percentage(user):
    stats = get_goal_stats(user)
    if stats["total"] == 0:
        return 0
    return int((stats["completed"] / stats["total"]) * 100)


def get_skill_wise_analytics(user):
    return SkillProgress.objects.filter(user=user) \
        .values('skill__title') \
        .annotate(total_time=Sum('actual_time')) \
        .order_by('-total_time')


def get_goal_completion_by_skill(user):
    return SkillGoal.objects.filter(user=user) \
        .values('skill__title') \
        .annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True))
        )


def get_streak(user):
    streak = 0
    today = date.today()

    while True:
        exists = SkillProgress.objects.filter(
            user=user,
            date=today - timedelta(days=streak)
        ).exists()

        if exists:
            streak += 1
        else:
            break

    return streak


def get_productivity_score(user):
    weekly = get_weekly_progress(user)
    streak = get_streak(user)
    completion = get_goal_completion_percentage(user)

    score = (streak * 2) + (weekly * 1.5) + (completion * 1.2)
    return round(score, 2)


def get_weekly_chart_data(user):
    today = date.today()
    labels = []
    data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        total = SkillProgress.objects.filter(
            user=user,
            date=day
        ).aggregate(sum=Sum('actual_time'))['sum'] or 0
        labels.append(day.strftime("%a"))
        data.append(float(total))

    return labels, data


def get_monthly_chart_data(user):
    today = date.today()
    labels = []
    data = []

    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        total = SkillProgress.objects.filter(
            user=user,
            date=day
        ).aggregate(sum=Sum('actual_time'))['sum'] or 0
        labels.append(day.strftime("%d %b"))
        data.append(float(total))

    return labels, data

# =====================================================
# INTERACTIVE DASHBOARD WITH BLUE-GREY COLOR PALETTE
# =====================================================
# =====================================================
# INTERACTIVE DASHBOARD WITH BLUE-GREY COLOR PALETTE
# =====================================================
@login_required
def dashboard(request):
    user = request.user
    today = date.today()

    # Blue-Grey Color Palette
    colors = {
        'primary': '#2563eb',      # Blue-600
        'secondary': '#3b82f6',     # Blue-500
        'tertiary': '#60a5fa',      # Blue-400
        'light': '#93c5fd',         # Blue-300
        'extra_light': '#dbeafe',   # Blue-100
        'grey_dark': '#1f2937',     # Gray-800
        'grey_medium': '#4b5563',   # Gray-600
        'grey_light': '#9ca3af',    # Gray-400
        'grey_extra_light': '#e5e7eb', # Gray-200
        'success': '#10b981',        # Emerald-500
        'warning': '#f59e0b',        # Amber-500
        'danger': '#ef4444',         # Red-500
        'background': '#f9fafb'      # Gray-50
    }

    # -----------------------------
    # Basic Stats
    # -----------------------------
    total_skills = Skill.objects.filter(user=user).count()
    active_skills = Skill.objects.filter(user=user, is_active=True).count()
    completed_skills = Skill.objects.filter(user=user, is_completed=True).count()

    goal_stats = get_goal_stats(user)
    goal_completion = get_goal_completion_percentage(user)

    total_study_time = get_total_study_time(user)
    today_progress = get_today_progress(user)
    weekly_progress = get_weekly_progress(user)
    monthly_progress = get_monthly_progress(user)

    streak = get_streak(user)
    productivity_score = get_productivity_score(user)

    # Advanced stats
    total_days_active = SkillProgress.objects.filter(user=user).values('date').distinct().count()
    avg_daily_time = total_study_time / total_days_active if total_days_active > 0 else 0
    
    skills = Skill.objects.filter(user=user)

    # Skill performance data for tables
    skill_performance = []
    for skill in skills:
        skill_progress = SkillProgress.objects.filter(user=user, skill=skill)
        if skill_progress.exists():
            total = skill_progress.aggregate(total=Sum('actual_time'))['total'] or 0
            avg = skill_progress.aggregate(avg=Avg('actual_time'))['avg'] or 0
            days = skill_progress.count()
            consistency = (days / 30) * 100 if days > 0 else 0
            
            skill_performance.append({
                'skill': skill.title,
                'total': round(total, 1),
                'avg': round(avg, 1),
                'days': days,
                'consistency': round(consistency, 1)
            })
    
    skill_performance.sort(key=lambda x: x['total'], reverse=True)

    # -----------------------------
    # Skill-wise Charts
    # -----------------------------
    skill_charts = []

    for index, skill in enumerate(skills):
        skill_progress = SkillProgress.objects.filter(user=user, skill=skill)
        skill_goals = SkillGoal.objects.filter(user=user, skill=skill)

        # ===== Monthly Bar Chart =====
        months = []
        monthly_data = []

        for i in range(5, -1, -1):
            month_date = today - timedelta(days=30*i)
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            
            total = skill_progress.filter(
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('actual_time'))['total'] or 0

            months.append(month_date.strftime('%b'))
            monthly_data.append(total)

        bar_fig = go.Figure()
        bar_fig.add_trace(go.Bar(
            x=months,
            y=monthly_data,
            text=[f"{d:.1f}h" for d in monthly_data],
            textposition='outside',
            marker_color=colors['primary'],
            marker_line_color=colors['grey_dark'],
            marker_line_width=1.5,
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>Hours: %{y:.1f}<extra></extra>'
        ))

        bar_fig.update_layout(
            title=f"{skill.title} - Monthly Progress",
            height=300,
            margin=dict(l=40, r=40, t=50, b=40),
            paper_bgcolor='white',
            plot_bgcolor=colors['background'],
            font=dict(family="Arial, sans-serif", size=11, color=colors['grey_medium']),
            showlegend=False
        )
        
        # Only include plotlyjs for the first chart
        include_js = True if index == 0 else False
        bar_div = plot(bar_fig, output_type='div', include_plotlyjs=include_js, config={'displayModeBar': False})

        # ===== Pie Chart (Goals) =====
        completed = skill_goals.filter(is_completed=True).count()
        active = skill_goals.filter(is_completed=False).count()

        if completed + active > 0:
            pie_fig = go.Figure(data=[go.Pie(
                labels=["Completed", "Active"],
                values=[completed, active],
                hole=0.5,
                marker_colors=[colors['success'], colors['warning']],
                textinfo='label+percent',
                textposition='outside',
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
                showlegend=False
            )])
        else:
            pie_fig = go.Figure()
            pie_fig.add_annotation(
                text="No Goals",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color=colors['grey_light'])
            )
            pie_fig.update_layout(
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )

        pie_fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor='white',
            plot_bgcolor=colors['background'],
            font=dict(family="Arial, sans-serif", size=11, color=colors['grey_medium'])
        )
        pie_div = plot(pie_fig, output_type='div', include_plotlyjs=False, config={'displayModeBar': False})

        # ===== 30 Day Line Chart =====
        labels = []
        data = []

        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            total = skill_progress.filter(date=day).aggregate(
                total=Sum('actual_time')
            )['total'] or 0

            labels.append(day.strftime("%d %b"))
            data.append(total)

        # Calculate 7-day moving average
        moving_avg = []
        for i in range(len(data)):
            if i < 6:
                moving_avg.append(None)
            else:
                avg = sum(data[i-6:i+1]) / 7
                moving_avg.append(round(avg, 1))

        line_fig = go.Figure()
        line_fig.add_trace(go.Scatter(
            x=labels,
            y=data,
            mode='lines+markers',
            name='Daily',
            line=dict(color=colors['primary'], width=2),
            marker=dict(size=6, color=colors['primary']),
            hovertemplate='<b>%{x}</b><br>Hours: %{y:.1f}<extra></extra>'
        ))
        
        line_fig.add_trace(go.Scatter(
            x=labels,
            y=moving_avg,
            mode='lines',
            name='7-Day Avg',
            line=dict(color=colors['grey_medium'], width=2, dash='dash'),
            hovertemplate='<b>%{x}</b><br>Avg: %{y:.1f}h<extra></extra>'
        ))

        line_fig.update_layout(
            title=f"{skill.title} - Last 30 Days",
            height=300,
            hovermode='x unified',
            margin=dict(l=40, r=40, t=50, b=40),
            paper_bgcolor='white',
            plot_bgcolor=colors['background'],
            font=dict(family="Arial, sans-serif", size=11, color=colors['grey_medium']),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10)
            )
        )
        line_div = plot(line_fig, output_type='div', include_plotlyjs=False, config={'displayModeBar': False})

        # ===== Gauge Chart =====
        total_goal = skill_goals.aggregate(
            total=Sum('daily_study_hours')
        )['total'] or 0

        achieved = skill_progress.aggregate(
            total=Sum('actual_time')
        )['total'] or 0

        percent = int((achieved / total_goal) * 100) if total_goal > 0 else 0
        percent = min(percent, 100)

        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percent,
            title={'text': "Progress %"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100], 'tickcolor': colors['grey_medium']},
                'bar': {'color': colors['primary']},
                'bgcolor': 'white',
                'borderwidth': 2,
                'bordercolor': colors['grey_light'],
                'steps': [
                    {'range': [0, 33], 'color': colors['extra_light']},
                    {'range': [33, 66], 'color': colors['light']},
                    {'range': [66, 100], 'color': colors['tertiary']}
                ]
            }
        ))

        gauge_fig.update_layout(
            height=150,
            margin=dict(l=30, r=30, t=30, b=30),
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif", color=colors['grey_medium'])
        )
        gauge_div = plot(gauge_fig, output_type='div', include_plotlyjs=False, config={'displayModeBar': False})

        skill_charts.append({
            "skill": skill,
            "bar_div": bar_div,
            "pie_div": pie_div,
            "line_div": line_div,
            "gauge_div": gauge_div,
            "percent": percent,
            "total_hours": round(achieved, 1),
            "avg_daily": round(skill_progress.aggregate(avg=Avg('actual_time'))['avg'] or 0, 1),
            "total_days": skill_progress.count()
        })

    # -----------------------------
    # Overall Chart (Dual Axis)
    # -----------------------------
    labels = []
    daily_data = []
    cumulative_data = []
    cumulative = 0

    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        total = SkillProgress.objects.filter(
            user=user,
            date=day
        ).aggregate(total=Sum('actual_time'))['total'] or 0

        labels.append(day.strftime("%d %b"))
        daily_data.append(total)

        cumulative += total
        cumulative_data.append(cumulative)

    overall_fig = make_subplots(specs=[[{"secondary_y": True}]])

    overall_fig.add_trace(
        go.Bar(
            x=labels, 
            y=daily_data, 
            name="Daily Hours",
            marker_color=colors['primary'],
            opacity=0.7,
            hovertemplate='<b>%{x}</b><br>Hours: %{y:.1f}<extra></extra>'
        ),
        secondary_y=False
    )

    overall_fig.add_trace(
        go.Scatter(
            x=labels, 
            y=cumulative_data,
            mode='lines+markers',
            name="Cumulative Hours",
            line=dict(color=colors['grey_dark'], width=3),
            marker=dict(size=8, color=colors['grey_dark']),
            hovertemplate='<b>%{x}</b><br>Total: %{y:.1f}h<extra></extra>'
        ),
        secondary_y=True
    )

    overall_fig.update_layout(
        title="Overall Progress (Last 30 Days)",
        height=400,
        hovermode='x unified',
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor='white',
        plot_bgcolor=colors['background'],
        font=dict(family="Arial, sans-serif", color=colors['grey_medium']),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    overall_fig.update_xaxes(tickangle=45)
    overall_fig.update_yaxes(title_text="Daily Hours", secondary_y=False, gridcolor=colors['grey_extra_light'])
    overall_fig.update_yaxes(title_text="Cumulative Hours", secondary_y=True, gridcolor=colors['grey_extra_light'])

    overall_div = plot(overall_fig, output_type='div', include_plotlyjs=False, config={'displayModeBar': False})

    # -----------------------------
    # Heatmap (Last 4 Weeks) - FIXED COLORBAR
    # -----------------------------
    heat_data = []
    week_labels = []
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    for w in range(4):
        week = []
        start = today - timedelta(days=28 - w*7)

        for d in range(7):
            day = start + timedelta(days=d)
            total = SkillProgress.objects.filter(
                user=user,
                date=day
            ).aggregate(total=Sum('actual_time'))['total'] or 0

            week.append(round(total, 1))

        heat_data.append(week)
        week_labels.append(f"Week {w+1}")

    heat_fig = go.Figure(data=go.Heatmap(
        z=heat_data,
        x=day_labels,
        y=week_labels,
        colorscale='Blues',
        text=[[f"{h}h" for h in row] for row in heat_data],
        texttemplate="%{text}",
        textfont={"size": 10, "color": "white"},
        hoverongaps=False,
                # Alternative colorbar configuration (if titleside still causes issues)
        colorbar=dict(
            title=dict(
                text="Hours",
                side="right"
    )
        )
))
                         
    heat_fig.update_layout(
        title="Weekly Activity Heatmap",
        height=300,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor='white',
        plot_bgcolor=colors['background'],
        font=dict(family="Arial, sans-serif", color=colors['grey_medium'])
    )
    heatmap_div = plot(heat_fig, output_type='div', include_plotlyjs=False, config={'displayModeBar': False})

    # -----------------------------
    # Weekly Chart
    # -----------------------------
    weekly_labels, weekly_data = get_weekly_chart_data(user)

    weekly_fig = go.Figure(data=[
        go.Bar(
            x=weekly_labels, 
            y=weekly_data,
            marker_color=colors['secondary'],
            marker_line_color=colors['grey_dark'],
            marker_line_width=1.5,
            text=[f"{d:.1f}h" for d in weekly_data],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Hours: %{y:.1f}<extra></extra>'
        )
    ])

    weekly_fig.update_layout(
        title="This Week's Progress",
        height=300,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor='white',
        plot_bgcolor=colors['background'],
        font=dict(family="Arial, sans-serif", color=colors['grey_medium']),
        showlegend=False
    )
    weekly_div = plot(weekly_fig, output_type='div', include_plotlyjs=False, config={'displayBarMode': False})

    # -----------------------------
    # Recent Progress
    # -----------------------------
    recent_progress = SkillProgress.objects.filter(user=user).select_related('skill').order_by('-date', '-id')[:10]
    
    # -----------------------------
    # Notes
    # -----------------------------
    notes = NoteLibrary.objects.filter(user=user).select_related('skill').order_by('-uploaded_at')[:10]

    # -----------------------------
    # Context
    # -----------------------------
    context = {
        "total_skills": total_skills,
        "active_skills": active_skills,
        "completed_skills": completed_skills,
        "goal_total": goal_stats["total"],
        "goal_completed": goal_stats["completed"],
        "goal_active": goal_stats["active"],
        "goal_completion": goal_completion,
        "total_study_time": round(total_study_time, 1),
        "today_progress": round(today_progress, 1),
        "weekly_progress": round(weekly_progress, 1),
        "monthly_progress": round(monthly_progress, 1),
        "streak": streak,
        "productivity_score": round(productivity_score, 1),
        "avg_daily_time": round(avg_daily_time, 1),
        "total_days_active": total_days_active,
        "skill_charts": skill_charts,
        "overall_div": overall_div,
        "heatmap_div": heatmap_div,
        "weekly_div": weekly_div,
        "skill_performance": skill_performance[:5],
        "recent_progress": recent_progress,
        "notes": notes,
    }

    return render(request, "user/dashboard.html", context)


# =====================================================
# API ENDPOINTS FOR INTERACTIVE UPDATES
# =====================================================

@login_required
def get_skill_data_api(request, skill_id):
    """API endpoint to get real-time skill data"""
    user = request.user
    skill = get_object_or_404(Skill, id=skill_id, user=user)
    
    progress_data = SkillProgress.objects.filter(skill=skill).order_by('date')
    
    data = {
        'skill': {
            'id': skill.id,
            'title': skill.title,
            'proficiency': skill.proficiency_level,
            'is_active': skill.is_active,
            'is_completed': skill.is_completed,
        },
        'stats': {
            'total_hours': progress_data.aggregate(total=Sum('actual_time'))['total'] or 0,
            'total_days': progress_data.count(),
            'avg_daily': progress_data.aggregate(avg=Avg('actual_time'))['avg'] or 0,
        }
    }
    
    return JsonResponse(data)


@login_required
def refresh_dashboard_api(request):
    """API endpoint to refresh dashboard data"""
    days = int(request.GET.get('days', 30))
    # Implementation for partial updates
    return JsonResponse({'status': 'success'})