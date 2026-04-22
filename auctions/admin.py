from django.contrib import admin
from django.utils import timezone

from .models import Auction, AuctionImage, Bid, BidderProfile


class AuctionImageInline(admin.TabularInline):
    model = AuctionImage
    extra = 1


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("title", "starting_price", "current_price", "start_at", "end_at", "is_active", "status_label")
    list_filter = ("is_active", "start_at", "end_at")
    search_fields = ("title", "description")
    inlines = [AuctionImageInline]
    readonly_fields = ("current_price", "created_at", "updated_at")
    fields = ("title", "description", "starting_price", "current_price", "start_at", "end_at", "is_active")

    def status_label(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return "Closed"
        if now < obj.start_at:
            return "Scheduled"
        if now >= obj.end_at:
            return "Ended"
        return "Open"

    status_label.short_description = "Status"


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("auction", "bidder", "amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("auction__title", "bidder__username", "bidder__bidderprofile__bidder_code")
    readonly_fields = ("auction", "bidder", "amount", "created_at")


@admin.register(BidderProfile)
class BidderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bidder_code")
    search_fields = ("user__username", "bidder_code")
