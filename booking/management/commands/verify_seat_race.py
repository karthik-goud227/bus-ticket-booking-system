"""Race independent Oracle sessions for one trip seat, then clean up."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone

from booking.models import Booking, Bus, Seat, Trip, TripSeat
from booking.services import BookingConflict, hold_seats


def compete(barrier, user_id, trip_id, seat_id):
    """Each thread opens its own database session before the shared start."""
    connections.close_all()
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT SYS_CONTEXT('USERENV', 'SID') FROM dual")
            session_id = str(cursor.fetchone()[0])
        barrier.wait(timeout=60)
        user = get_user_model().objects.get(id=user_id)
        trip = Trip.objects.get(id=trip_id)
        try:
            hold_seats(user=user, trip=trip, seat_ids=[seat_id])
            return ("success", session_id, "")
        except BookingConflict as error:
            return ("conflict", session_id, str(error))
    except Exception as error:
        return ("error", "", f"{type(error).__name__}: {error}")
    finally:
        connections.close_all()


class Command(BaseCommand):
    help = "Race 20 separate Oracle sessions for one seat; expect one success and 19 conflicts."

    def add_arguments(self, parser):
        parser.add_argument("--clients", type=int, default=20)

    def handle(self, *args, **options):
        clients = options["clients"]
        if not 2 <= clients <= 30:
            raise CommandError("Choose between 2 and 30 clients.")
        marker = uuid4().hex[:10].upper()
        user = bus = seat = trip = inventory = None
        try:
            user = get_user_model().objects.create_user(
                username=f"race_{marker.lower()}", password=uuid4().hex
            )
            bus = Bus.objects.create(
                registration_number=f"RACE{marker}", operator_name="Race test", bus_type="Test"
            )
            seat = Seat.objects.create(bus=bus, number="R1")
            depart = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Race A", destination="Race B",
                departure_at=depart, arrival_at=depart + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            barrier = Barrier(clients)
            with ThreadPoolExecutor(max_workers=clients) as executor:
                results = list(executor.map(
                    lambda _: compete(barrier, user.id, trip.id, inventory.id), range(clients)
                ))
            successes = sum(result[0] == "success" for result in results)
            conflicts = sum(result[0] == "conflict" for result in results)
            session_ids = {result[1] for result in results if result[1]}
            errors = [result[2] for result in results if result[0] == "error"]
            held_count = Booking.objects.filter(trip=trip, status=Booking.Status.HELD).count()
            inventory.refresh_from_db()
            self.stdout.write(
                f"{clients} requests; {len(session_ids)} distinct Oracle sessions; "
                f"{successes} successful hold; {conflicts} seat conflicts; {held_count} held booking."
            )
            if errors or successes != 1 or conflicts != clients - 1 or held_count != 1 or len(session_ids) != clients:
                raise CommandError(f"Race failed: {errors or results}")
            if inventory.status != TripSeat.Status.HELD or inventory.booking_id is None:
                raise CommandError("Inventory did not record the winning booking.")
            self.stdout.write(self.style.SUCCESS("PASS: one winner and no double booking."))
        finally:
            if trip is not None:
                TripSeat.objects.filter(trip=trip).delete()
                Booking.objects.filter(trip=trip).delete()
                Trip.objects.filter(id=trip.id).delete()
            if seat is not None:
                Seat.objects.filter(id=seat.id).delete()
            if bus is not None:
                Bus.objects.filter(id=bus.id).delete()
            if user is not None:
                get_user_model().objects.filter(id=user.id).delete()
            self.stdout.write("Race test data removed.")
