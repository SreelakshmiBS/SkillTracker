from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class SkillProfile(models.Model):
    ROLE_CHOICES=[
        ('student','Student'),
        ('employee','Employee'),
        ('freelancer','Freelancer'),
        ('other','Other')
]
    EXPERIENCE_LEVEL_CHOICES=[
        ('beginner','Beginner'),
        ('intermediate','Intermediate'),
        ('expert','Expert')
]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    education = models.TextField(blank=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    
    def __str__(self):
        return f"{self.user.username}'s Skill Profile"