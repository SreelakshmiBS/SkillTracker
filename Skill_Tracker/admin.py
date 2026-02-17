from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Skill, SkillGoal, SkillProgress, NoteLibrary

admin.site.register(Skill)
admin.site.register(SkillGoal)
admin.site.register(SkillProgress)
admin.site.register(NoteLibrary)
