import random

from .models import BidderProfile


def create_bidder_profile(user):
    code = random.randint(100000, 999999)
    while BidderProfile.objects.filter(bidder_code=code).exists():
        code = random.randint(100000, 999999)
    return BidderProfile.objects.create(user=user, bidder_code=code)
