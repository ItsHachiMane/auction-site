from django.urls import path
from .views import auction_detail, auction_fragment, auction_list, client_dashboard, dashboard, my_history, signup, toggle_watchlist

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("auctions/", auction_list, name="auction_list"),
    path("auction/<int:pk>/", auction_detail, name="auction_detail"),
    path("auction/<int:pk>/fragment/", auction_fragment, name="auction_fragment"),
    path("auction/<int:pk>/watch/", toggle_watchlist, name="toggle_watchlist"),
    path("history/", my_history, name="my_history"),
    path("client/", client_dashboard, name="client_dashboard"),
    path("signup/", signup, name="signup"),
]
