# Multiple buses and trip scheduling

The database separates a **physical bus** from its **scheduled trips**.
`BOOKING_BUS` has a unique registration number and a bus type; `BOOKING_SEAT`
stores that bus's physical seats. One bus can have many trips. Each trip gets
its own `BOOKING_TRIPSEAT` inventory, so seat 1 on Monday and seat 1 on
Wednesday can be sold independently. Multiple buses may run at the same time.

## Demonstration fleet

After setting `DB_PASSWORD` and applying migrations:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_fleet
```

The command creates four separate demo registrations with AC Seater, AC
Sleeper, Non-AC Seater and Mini Bus types. Each has two future trips, with
different routes, fares, and seat counts. It uses `get_or_create`, so rerunning
it on the same date does not duplicate those trips or their seat inventory.
It does not delete existing buses, bookings, or passengers. On a later date,
the relative future dates change and another set of future trips may be added;
review the admin trip list before rerunning it then.

`seed_demo` is the older small example. It is optional and independent of
`seed_fleet`. Administrators can also create any number of real demo buses
and trips manually in `/admin/`.

## Schedule integrity rule

Two active trips for the **same bus** overlap when:

```text
existing.departure_at < new.arrival_at
AND existing.arrival_at > new.departure_at
```

The interval is treated as `[departure, arrival)`. One trip can therefore
start exactly when another arrives. A cancelled trip no longer reserves its
bus's schedule slot. A different bus can depart at the same time.

The admin form checks this before saving to show a readable error. Migration
`0009_trip_schedule_guard.py` also creates Oracle compound trigger
`TRG_TRIP_NO_OVERLAP`: it locks the bus row for changes to active trips and
checks the trip table after the statement. This protects direct SQL writes
and serializes concurrent schedule changes for one bus. The existing
`CK_TRIP_TIMES` constraint separately requires arrival after departure.

Run the rollback-only database probe:

```powershell
.\.venv\Scripts\python.exe manage.py verify_trip_schedule
```

Expected results: Oracle rejects overlap with `ORA-20011`, while an adjacent
trip and a concurrent trip on another bus succeed. The probe removes its own
test data. In SQL Developer, run the following as `BUSBOOKING` to inspect the
current fleet and schedules:

```sql
SELECT b.registration_number, b.bus_type, t.origin, t.destination,
       t.departure_at, t.arrival_at, t.is_cancelled
FROM booking_bus b
JOIN booking_trip t ON t.bus_id = b.id
ORDER BY b.registration_number, t.departure_at;
```
