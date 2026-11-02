# Fleet layouts, daily trips, and ticket details

## Apply to the existing Oracle database

In the project PowerShell window, set `DB_PASSWORD` as described in the README, then run:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py upgrade_fleet
.\.venv\Scripts\python.exe manage.py generate_daily_trips --days 14
.\.venv\Scripts\python.exe manage.py verify_fleet_layout
```

Restart the Django server after migrating. `upgrade_fleet` keeps existing buses,
bookings and seat numbers. It only adds missing physical seats and corresponding
trip-seat inventory. Repeating it is safe. All current buses become at least
24-seat vehicles. Selected buses receive three places per row, a second deck,
or sleeping berths; other buses keep a four-seat layout. The admin shows the
layout attributes on Bus and Seat pages. When newly added inventory appears on
a trip with a waiting list, the booking service offers those places to waiting
passengers first in FIFO order.

`generate_daily_trips` creates dated Trip rows from RecurringTrip templates.
Each dated Trip has its own TripSeat inventory and can be booked independently.
The command adds six default daily route templates for three demo buses, then
materializes the next 14 days. It skips any time window already occupied by
that bus. Existing Oracle trip-overlap enforcement remains in force. Repeating
the command extends the rolling window without deleting old trips. The
`start_team.ps1` launcher runs this refresh each time it starts. Staff can
edit or disable the templates in Django admin, then rerun the command.

## Database relationships

- `Bus` stores the number of places per row and whether it has an upper deck.
- `Seat` belongs to a Bus and stores its deck and seat type (`STANDARD` or `BED`).
- `RecurringTrip` stores the daily route, departure time, duration, fare, and bus.
  Oracle uniqueness and check constraints reject duplicate bus departure times,
  invalid durations/fares, and same-city routes.
- `Trip.schedule` optionally points to the template that generated it. Admin
  trips entered manually can leave this link empty.
- `TripSeat` remains the inventory source of truth for each dated trip.
- `Booking` now stores the passenger name and contact phone entered during a
  direct booking or waiting-list offer acceptance. Existing records retain their
  account username as a ticket fallback.

Trip listings show available/full state and approximate duration. The ticket
shows passenger contact, booking date, departure and approximate arrival,
and the deck/berth for each allocated place. A booking can hold any number of
available places; all selected rows are still locked and committed atomically.
