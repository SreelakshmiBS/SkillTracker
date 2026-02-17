from django.db import models
from django.contrib.auth.models import User
import datetime
from datetime import date
# Create your models here.
class Skill(models.Model):

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='skills'
    )

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    proficiency_level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner'
    )

    start_date = models.DateField(auto_now_add=True)
    last_practiced = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # If skill is completed → mark all goals completed
        if self.is_completed:
            self.goals.update(is_completed=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"
    
class SkillGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    skill = models.ForeignKey('Skill', on_delete=models.CASCADE, related_name='goals')

    goal_description = models.TextField()

    start_date = models.DateField(auto_now_add=True)
    target_date = models.DateField()

    daily_study_hours = models.PositiveIntegerField(
        help_text="Hours per day you can study",
        blank=True,
        null=True
    )

    is_completed = models.BooleanField(default=False)

    roadmap = models.FileField(upload_to='roadmaps/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # If goal is completed → mark skill completed
        if self.skill.goals.filter(is_completed=False).count() == 0:
            self.skill.is_completed = True
            self.skill.save()


    # -------- SMART CALCULATIONS --------
    @property
    def total_days(self):
        return max((self.target_date - self.start_date).days, 0)

    @property
    def total_hours_required(self):
        if not self.daily_study_hours:
            return 0
        return self.total_days * self.daily_study_hours

    @property
    def days_completed(self):
        return max((date.today() - self.start_date).days, 0)

    @property
    def progress_percentage(self):
        if self.total_days == 0:
            return 0
        return min(int((self.days_completed / self.total_days) * 100), 100)
    
class SkillProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skill_progress')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='progress_entries')
    date = models.DateField(auto_now_add=True)
    planned_time =models.PositiveIntegerField(help_text="daily_study time in hours",default=0)
    actual_time = models.PositiveIntegerField(help_text="Actual study time in hours")
    extra_time = models.PositiveIntegerField(help_text="Extra study time in hours", default=0)
    project_done = models.BooleanField(default=False)
    project_update = models.TextField(blank=True, null=True)
    certification_done = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    topics_done = models.TextField(blank=True, null=True)
    new_topic_done = models.BooleanField(default=False)
    topic_notes =models.BooleanField(default=False)
    notes_file = models.FileField(upload_to='notes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confidence_level = models.PositiveIntegerField(help_text="Confidence level from 1 to 10", default=5)
    updated_at = models.DateTimeField(auto_now=True)
    feedback_or_points = models.TextField(blank=True, null=True)
    marks_yourself = models.PositiveIntegerField(help_text="Rate yourself from 1 to 10", default=5)
    is_completed = models.BooleanField(default=False)

class NoteLibrary(models.Model):
    NOTE_TYPES = [
        ('notes', 'Notes'),
        ('roadmap', 'Roadmap'),
        ('reference', 'Reference'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="notes")

    title = models.CharField(max_length=200)
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES)
    file = models.FileField(upload_to="note_library/")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.skill.title}"
