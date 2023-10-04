from django.db import models
from django.conf import settings

class Facing(models.Model):
    """
    RCD Facing.

    https://carcc.org/rcd-professionalization/facings/
    """
    class Manager(models.Manager):
        def get_by_natural_key(self, facing: str):
            return self.get(slug=facing)
        
    objects = Manager()

    slug = models.CharField(max_length=50, unique=True)
    index = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Position of this facing in the list of facings.")

    def natural_key(self):
        return (self.slug,)

    def __str__(self):
        return self.slug
    
    class Meta:
        verbose_name = "RCD facing"
        ordering = ["index", "slug"]
    
class FacingContent(models.Model):
    """
    Language-specific content for a facing.
    """
    class Manager(models.Manager):
        def get_by_natural_key(self, facing: str, language: str):
            return self.get(facing__slug=facing, language=language)
        
    objects = Manager()

    facing = models.ForeignKey(
        Facing,
        on_delete=models.CASCADE,
        related_name="contents",
    )
    language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="en",
    )
    display_name = models.CharField(max_length=255)
    description = models.TextField()

    def natural_key(self):
        return (self.facing.slug, self.language)

    def __str__(self):
        return f"[{self.language.upper()}] {self.facing}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facing", "language"], name="%(app_label)s_%(class)s_unique"
            )
        ]
