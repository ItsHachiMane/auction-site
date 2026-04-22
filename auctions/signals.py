import random

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BidderProfile


@receiver(post_save, sender=User)
def assign_bidder_code(sender, instance, created, **kwargs):
    if created and not instance.is_staff and not instance.is_superuser:
        code = random.randint(100000, 999999)
        while BidderProfile.objects.filter(bidder_code=code).exists():
            code = random.randint(100000, 999999)
        BidderProfile.objects.create(user=instance, bidder_code=code)
