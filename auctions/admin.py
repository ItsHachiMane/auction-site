from django.contrib import admin
from django.utils import timezone

from .models import Auction, AuctionImage, Bid, BidAudit, BidderProfile, Notification, WatchlistItem


class AuctionImageInline(admin.TabularInline):
    model = AuctionImage
    extra = 1


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("title", "starting_price", "reserve_price", "bid_increment", "current_price", "start_at", "end_at", "is_active", "status_label")
    list_filter = ("is_active", "start_at", "end_at")
    search_fields = ("title", "description", "categories", "admin_notes")
    inlines = [AuctionImageInline]
    readonly_fields = ("current_price", "created_at", "updated_at")
    fields = ("title", "description", "starting_price", "reserve_price", "bid_increment", "current_price", "start_at", "end_at", "is_active", "categories", "admin_notes")
    actions = ["close_auctions", "reopen_auctions", "end_and_award_auctions"]

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

    @admin.action(description="Close selected auctions")
    def close_auctions(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Reopen selected auctions")
    def reopen_auctions(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="End selected auctions and award to current highest bidder")
    def end_and_award_auctions(self, request, queryset):
        for auction in queryset:
            auction.is_active = False
            auction.end_at = timezone.now()
            auction.save(update_fields=["is_active", "end_at", "updated_at"])


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("auction", "bidder", "amount", "created_at")
    list_filter = ("created_at",)
    search_fields = ("auction__title", "bidder__username", "bidder__bidderprofile__bidder_code")
    readonly_fields = ("auction", "bidder", "amount", "created_at")


@admin.register(BidAudit)
class BidAuditAdmin(admin.ModelAdmin):
    list_display = ("auction", "bidder", "amount", "created_at", "note")
    search_fields = ("auction__title", "bidder__username", "note")


@admin.register(BidderProfile)
class BidderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bidder_code")
    search_fields = ("user__username", "bidder_code")


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "auction", "created_at")
    search_fields = ("user__username", "auction__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "read_at")
    search_fields = ("user__username", "message")
