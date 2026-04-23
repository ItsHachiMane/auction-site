from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Auction(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bid_increment = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    categories = models.CharField(max_length=255, blank=True, help_text="Comma-separated categories/tags")
    admin_notes = models.TextField(blank=True)
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

    def extend_if_soft_close(self):
        remaining = self.time_left_seconds
        if remaining <= 60 and self.is_open:
            self.end_at = timezone.now() + timedelta(minutes=5)
            self.save(update_fields=["end_at", "updated_at"])

    @property
    def winning_bid(self):
        return self.bids.select_related("bidder__bidderprofile").order_by("-amount", "created_at").first()

    @property
    def winner(self):
        bid = self.winning_bid
        return bid.bidder if bid else None

    @property
    def sold(self):
        if self.reserve_price is None:
            return bool(self.winning_bid)
        return bool(self.winning_bid and self.winning_bid.amount >= self.reserve_price)


class BidderProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bidder_code = models.PositiveIntegerField(unique=True)

    def __str__(self):
        return f"Bidder #{self.bidder_code}"


class WatchlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_items")
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="watchlist_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "auction")


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


class BidAudit(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name="audit_entries")
    bidder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def mark_read(self):
        self.read_at = timezone.now()
        self.save(update_fields=["read_at"])
