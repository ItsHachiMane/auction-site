from django.conf import settings
from django.db import models
from django.utils import timezone


class Auction(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_active and self.start_at <= now < self.end_at

    @property
    def time_left_seconds(self):
        now = timezone.now()
        if now >= self.end_at:
            return 0
        return int((self.end_at - now).total_seconds())

    def close_if_needed(self):
        if self.is_active and timezone.now() >= self.end_at:
            self.is_active = False
            self.save(update_fields=["is_active", "updated_at"])

    @property
    def winning_bid(self):
        return self.bids.select_related("bidder__bidderprofile").order_by("-amount", "created_at").first()


class BidderProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bidder_code = models.PositiveIntegerField(unique=True)

    def __str__(self):
        return f"Bidder #{self.bidder_code}"


class AuctionImage(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="auction_images/")
    alt_text = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="bids")
    bidder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-amount", "created_at"]
