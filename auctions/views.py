from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BidForm, SignupForm
from .models import Auction, Bid, WatchlistItem


def dashboard(request):
    auctions = Auction.objects.prefetch_related("images").order_by("-created_at")
    for auction in auctions:
        auction.close_if_needed()
    open_count = sum(1 for a in auctions if a.is_open)
    closed_count = auctions.count() - open_count
    return render(request, "auctions/dashboard.html", {
        "auctions": auctions,
        "open_count": open_count,
        "closed_count": closed_count,
        "total_count": auctions.count(),
    })


def auction_list(request):
    return dashboard(request)


def auction_detail(request, pk):
    auction = get_object_or_404(Auction.objects.prefetch_related("images", "bids__bidder__bidderprofile"), pk=pk)
    auction.close_if_needed()
    highest_bid = auction.bids.aggregate(max_amount=Max("amount"))["max_amount"]
    next_min = highest_bid if highest_bid is not None else auction.starting_price
    form = BidForm(initial={"amount": next_min})
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        if not auction.is_open:
            return HttpResponseForbidden("Auction is closed.")
        form = BidForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            if amount <= next_min:
                form.add_error("amount", f"Bid must be higher than {next_min}.")
            else:
                with transaction.atomic():
                    auction = Auction.objects.select_for_update().get(pk=auction.pk)
                    auction.close_if_needed()
                    current_high = auction.bids.aggregate(max_amount=Max("amount"))["max_amount"]
                    floor = current_high if current_high is not None else auction.starting_price
                    if amount <= floor:
                        form.add_error("amount", f"Bid must be higher than {floor}.")
                    else:
                        Bid.objects.create(auction=auction, bidder=request.user, amount=amount)
                        auction.current_price = amount
                        auction.save(update_fields=["current_price", "updated_at"])
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
    return render(request, "auctions/history.html", {"bids": bids, "watched": watched})


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
