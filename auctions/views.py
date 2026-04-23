from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BidForm, ProfileForm, SignupForm
from .models import Auction, Bid, BidAudit, Notification, WatchlistItem


def dashboard(request):
    query = request.GET.get("q", "").strip()
    auctions = Auction.objects.prefetch_related("images")
    if query:
        auctions = auctions.filter(title__icontains=query)
    auctions = auctions.order_by("-created_at")
    for auction in auctions:
        auction.close_if_needed()
    open_count = sum(1 for a in auctions if a.is_open)
    closed_count = auctions.count() - open_count
    return render(request, "auctions/dashboard.html", {
        "auctions": auctions,
        "open_count": open_count,
        "closed_count": closed_count,
        "total_count": auctions.count(),
        "query": query,
    })


def auction_list(request):
    return dashboard(request)


def auction_detail(request, pk):
    auction = get_object_or_404(Auction.objects.prefetch_related("images", "bids__bidder__bidderprofile"), pk=pk)
    auction.close_if_needed()
    highest_bid = auction.bids.aggregate(max_amount=Max("amount"))["max_amount"]
    next_min = highest_bid if highest_bid is not None else auction.starting_price
    if highest_bid is not None:
        next_min = highest_bid + auction.bid_increment
    form = BidForm(initial={"amount": next_min})
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        if not auction.is_open:
            return HttpResponseForbidden("Auction is closed.")
        form = BidForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            if amount < next_min:
                form.add_error("amount", f"Bid must be at least {next_min}.")
            else:
                with transaction.atomic():
                    auction = Auction.objects.select_for_update().get(pk=auction.pk)
                    auction.close_if_needed()
                    current_high = auction.bids.aggregate(max_amount=Max("amount"))["max_amount"]
                    floor = current_high + auction.bid_increment if current_high is not None else auction.starting_price
                    if amount < floor:
                        form.add_error("amount", f"Bid must be at least {floor}.")
                    else:
                        Bid.objects.create(auction=auction, bidder=request.user, amount=amount)
                        BidAudit.objects.create(auction=auction, bidder=request.user, amount=amount, note="Bid placed")
                        auction.current_price = amount
                        auction.extend_if_soft_close()
                        auction.save(update_fields=["current_price", "updated_at", "end_at"])
                        Notification.objects.create(user=request.user, message=f"Your bid on {auction.title} was placed.")
                        messages.success(request, "Bid placed.")
                        return redirect("auction_detail", pk=auction.pk)

    bids = auction.bids.select_related("bidder__bidderprofile").order_by("-amount", "created_at")
    watched = request.user.is_authenticated and WatchlistItem.objects.filter(user=request.user, auction=auction).exists()
    return render(
        request,
        "auctions/auction_detail.html",
        {
            "auction": auction,
            "bids": bids,
            "form": form,
            "highest_bid": highest_bid,
            "is_open": auction.is_open,
            "now": timezone.now(),
            "time_left_seconds": auction.time_left_seconds,
            "images": auction.images.all(),
            "winning_bid": auction.winning_bid,
            "sold": auction.sold,
            "watched": watched,
        },
    )


def auction_fragment(request, pk):
    auction = get_object_or_404(Auction.objects.prefetch_related("bids__bidder__bidderprofile"), pk=pk)
    auction.close_if_needed()
    bids = auction.bids.select_related("bidder__bidderprofile").order_by("-amount", "created_at")
    return render(request, "auctions/partials/auction_fragment.html", {"auction": auction, "bids": bids, "winning_bid": auction.winning_bid, "time_left_seconds": auction.time_left_seconds, "is_open": auction.is_open, "sold": auction.sold})


@login_required
def toggle_watchlist(request, pk):
    auction = get_object_or_404(Auction, pk=pk)
    item = WatchlistItem.objects.filter(user=request.user, auction=auction)
    if item.exists():
        item.delete()
        messages.success(request, "Removed from watchlist.")
    else:
        WatchlistItem.objects.create(user=request.user, auction=auction)
        messages.success(request, "Added to watchlist.")
    return redirect("auction_detail", pk=auction.pk)


@login_required
def my_history(request):
    bids = Bid.objects.filter(bidder=request.user).select_related("auction").order_by("-created_at")
    watched = WatchlistItem.objects.filter(user=request.user).select_related("auction").order_by("-created_at")
    won = Bid.objects.filter(bidder=request.user, auction__end_at__lte=timezone.now()).select_related("auction").order_by("-created_at")
    return render(request, "auctions/history.html", {"bids": bids, "watched": watched, "won": won})


@login_required
def client_dashboard(request):
    profile = getattr(request.user, "bidderprofile", None)
    bid_count = Bid.objects.filter(bidder=request.user).count()
    watch_count = WatchlistItem.objects.filter(user=request.user).count()
    return render(request, "auctions/client_dashboard.html", {
        "profile": profile,
        "bid_count": bid_count,
        "watch_count": watch_count,
        "joined": request.user.date_joined,
    })


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("client_dashboard")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "auctions/profile_edit.html", {"form": form})


@login_required
def receipt(request, auction_id):
    auction = get_object_or_404(Auction.objects.select_related(), pk=auction_id)
    return render(request, "auctions/receipt.html", {"auction": auction, "winning_bid": auction.winning_bid, "sold": auction.sold})


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created.")
            return redirect("auction_list")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})
