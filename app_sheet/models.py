from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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


# file will be uploaded to MEDIA_ROOT / images / user_id / <filename>
def user_directory_path(self, filename):
    return 'images/{0}/{1}'.format(self.id, filename)


class Sheet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    system = models.CharField(verbose_name='RPG System', choices=SheetSystems.choices,
                              default=SheetSystems.NONE, max_length=12)
    name = models.CharField(verbose_name='Character Name', max_length=64)
    created = models.DateField(verbose_name='Date Created', auto_now_add=True)
    modified = models.DateField(verbose_name='Date Last Modified', auto_now=True)
    content = models.TextField(verbose_name='Definition')

    image1 = models.ImageField(verbose_name='Image #1', upload_to=user_directory_path,
                               null=True, blank=True, default=None)
    image2 = models.ImageField(verbose_name='Image #2', upload_to=user_directory_path,
                               null=True, blank=True, default=None)
    image3 = models.ImageField(verbose_name='Image #3', upload_to=user_directory_path,
                               null=True, blank=True, default=None)

    is_shared = models.BooleanField(default=False, verbose_name='Sheet is shared')
    is_template = models.BooleanField(default=False, verbose_name='Sheet is a template')

    def clean(self):
        images = [self.image1, self.image2, self.image3]
        size = sum(im.size for im in images if im)
        if size > 5 * 1024 * 1024:
            raise ValidationError("Images too big. Total size of images cannot exceed 5MB")

    def __str__(self):
        return self.system + ' • ' + self.owner.username + ' • ' + self.name
