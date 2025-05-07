from django.db import models

class GraphLink(models.Model):
    search_query = models.CharField(max_length=255)
    link = models.CharField(max_length=255)

    def __str__(self):
        return self.search_query
