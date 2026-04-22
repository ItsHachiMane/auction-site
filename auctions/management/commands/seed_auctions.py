from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from auctions.models import Auction


class Command(BaseCommand):
    help = "Seed sample auctions"

    def handle(self, *args, **options):
        now = timezone.now()
        samples = [
            ("Vintage Watch", "Classic stainless steel watch.", 150, 24, ["watch1.jpg", "watch2.jpg"]),
            ("Gaming PC", "High-end desktop with strong specs.", 900, 12, ["pc1.jpg", "pc2.jpg"]),
            ("Designer Bag", "Limited edition bag in excellent condition.", 300, 48, ["bag1.jpg", "bag2.jpg"]),
        ]
        for title, desc, start, hours, _images in samples:
            Auction.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "starting_price": start,
                    "current_price": start,
                    "start_at": now,
                    "end_at": now + timedelta(hours=hours),
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded sample auctions."))
