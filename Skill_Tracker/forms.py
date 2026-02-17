from django import forms
from .models import *

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['title', 'description','proficiency_level', 'last_practiced','is_active']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Python, Django'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Short description (optional)'
            }),
            'proficiency_level': forms.Select(attrs={
                'class': 'form-control'
            }),
            'last_practiced': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
class SkillGoalForm(forms.ModelForm):
    class Meta:
        model = SkillGoal
        fields = [
            'skill',
            'goal_description',
            'target_date',
            'daily_study_hours',
            'roadmap',
        ]

        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control'}),
            'goal_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'target_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'daily_study_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hours per day'
            }),
            'skill': forms.Select(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # accept user
        super().__init__(*args, **kwargs)
        if user:
            self.fields['skill'].queryset = Skill.objects.filter(user=user)
            
class SkillProgressForm(forms.ModelForm):
    class Meta:
        model = SkillProgress
        fields = [
            'actual_time',
            'project_done',
            'project_update',
            'certification_done',
            'certificate_file',
            'topics_done',
            'new_topic_done',
            'topic_notes',
            'notes_file',
            'confidence_level',
            'feedback_or_points',
            'marks_yourself',
            'is_completed',
        ]

        widgets = {
            'actual_time': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Actual study time in hours'
            }),
            'project_done': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'project_update': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Project updates (optional)'
            }),
            'certification_done': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'certificate_file': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'topics_done': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Topics covered (optional)'
            }),
            'new_topic_done': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'topic_notes': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes_file': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'confidence_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'feedback_or_points': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Feedback or points (optional)'
            }),
            'marks_yourself': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

class NoteLibraryForm(forms.ModelForm):
    class Meta:
        model = NoteLibrary
        fields = ['title', 'note_type', 'file']
