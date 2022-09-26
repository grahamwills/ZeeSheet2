from django.contrib.auth.models import User
from django.db import models

class SheetSystems(models.TextChoices):
    NONE = "None", "No System"
    FATE = "Fate", "Fate"
    THIRTEENTH_AGE = "13th Age", "13th Age"
    DND4E = "D&D 4E", "D&D 4th Edition"
    PATHFINDER = "Pathfinder", "Pathfinder"
    NUMENERA = "Numenéra", "Numenéra"
    PENDRAGON = "Pendragon", "Pendragon"
    OTHER = "Other", "Other System"


class Sheet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    system = models.CharField(verbose_name='RPG System', choices=SheetSystems.choices,
                              default=SheetSystems.NONE, max_length=12)
    name = models.CharField(verbose_name='Character Name', max_length=64)
    created = models.DateField(verbose_name='Date Created', auto_now_add=True)
    modified = models.DateField(verbose_name='Date Last Modified', auto_now=True)
    content = models.TextField(verbose_name='Definition')
    is_shared = models.BooleanField(default=False, verbose_name='Sheet is shared')
    is_template = models.BooleanField(default=False, verbose_name='Sheet is a template')

    def __str__(self):
        return self.system + ' • ' + self.owner.username + ' • ' + self.name
