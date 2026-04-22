from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BidForm, SignupForm
from .models import Auction, Bid


def auction_list(request):
    auctions = Auction.objects.prefetch_related("images").order_by("-created_at")
    for auction in auctions:
        auction.close_if_needed()
    return render(request, "auctions/auction_list.html", {"auctions": auctions})


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
        },
    )


def auction_fragment(request, pk):
    auction = get_object_or_404(Auction.objects.prefetch_related("bids__bidder__bidderprofile"), pk=pk)
    auction.close_if_needed()
    bids = auction.bids.select_related("bidder__bidderprofile").order_by("-amount", "created_at")
    return render(request, "auctions/partials/auction_fragment.html", {"auction": auction, "bids": bids, "winning_bid": auction.winning_bid, "time_left_seconds": auction.time_left_seconds, "is_open": auction.is_open})


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
