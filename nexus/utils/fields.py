from django.db import models


class FloatChoices(float, models.Choices):
    """Class for creating enumerated float choices"""

    pass
