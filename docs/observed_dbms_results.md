# Observed DBMS results

These results were observed in the local Oracle 21c XE database on 1 November
2026. Re-run the linked commands and SQL before presenting if the data changes.

## Integrity and concurrency

- `python manage.py verify_integrity`: Oracle rejected a seat from another bus
  (`ORA-20001`), a booking from another trip (`ORA-20002`), and an offered seat
  from another trip (`ORA-20003`). The command rolled back its probe rows.
- `python manage.py verify_seat_race`: 20 requests used 20 distinct Oracle
  sessions for one seat. Exactly one hold succeeded, 19 conflicted, and one
  held booking remained. The command then removed its test rows.
- `python manage.py verify_atomic_hold`: an injected failure on the second
  seat of a two-seat hold left both seats available and created no booking.
  The command removed its test rows. This passed twice in separate runs.

## Live booking and reporting views

For trip 6, Kurnool to Vijayawada, bus 10901 had 10 inventory seats. Before
booking, `V_TRIP_OCCUPANCY` returned 0 booked, 10 available, and 0% occupancy.
After confirming seat 6 at ₹699, the joined occupancy and revenue views returned:

| Total seats | Booked | Available | Occupancy | Captured | Refunded | Net |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 1 | 9 | 10% | ₹699 | ₹0 | ₹699 |

## Cancellation and refund

A second ₹699 booking for seat 7 was confirmed and then cancelled. The
passenger booking list showed that booking as `CANCELLED` while the original
seat 6 booking remained `CONFIRMED`. The Oracle views then returned:

| Total seats | Booked | Available | Occupancy | Captured | Refunded | Net |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 1 | 9 | 10% | ₹1,398 | ₹699 | ₹699 |

This confirms that cancellation released seat 7 and recorded a simulated
refund without altering the original booking. Payments are simulated; no real
money was transferred.

## Waiting-list promotion and acceptance

After all 10 seats on trip 6 were confirmed, a second passenger joined the
waiting list. `V_WAITLIST_QUEUE` showed the passenger as `WAITING` at position
1. The first passenger then cancelled the original single-seat booking for
seat 6. Oracle showed the waiting entry as `OFFERED` with an assigned seat and
an expiry deadline. The waiting passenger accepted and confirmed the offered
seat 6. The final Oracle query returned `ACCEPTED`, 10 booked seats, 0
available seats, and 100% occupancy.

This demonstrates a timed offer and seat reuse after cancellation. Only one
waiting passenger was observed in this live scenario.

An isolated `verify_waitlist_fifo` run subsequently tested two waiting
passengers. The first received the cancelled seat; when that timed offer was
expired, the second received the seat and confirmed it. All three checks
passed, and the command removed its test rows. This verifies two-person FIFO
promotion and offer expiry. Concurrent queue joins remain a separate case.

An isolated `verify_waitlist_leave` run checked the new passenger exit flow.
`V_WAITLIST_QUEUE` assigned positions 1 and 2 to two waiting passengers.
After the first passenger received a cancelled seat and left the list, the
second passenger immediately received that offer. The Oracle view then showed
the second passenger at position 1. All three checks passed, and the command
removed its test rows.

## Trip-search execution plan

For the Kurnool-to-Vijayawada trip search, Oracle's `EXPLAIN PLAN` showed:

1. `INDEX RANGE SCAN` on `IDX_TRIP_SEARCH` for origin and destination.
2. `TABLE ACCESS BY INDEX ROWID` on `BOOKING_TRIP` for the matching row.

The plan lists departure time as a filter rather than an index access
condition; this distinction is useful when discussing the composite index.

Plan hash value: `3220378848`. Oracle reported dynamic sampling level 2.
The plan cost of 1 and displayed time of 00:00:01 are optimizer estimates,
not measured response times. The database currently contains very few trips,
so this observation does not establish an index performance gain.

## Backup and restore

Oracle Data Pump exported `BUSBOOKING` and successfully imported it into the
separate `BUSBOOKING_RESTORE` schema. Restored counts were 1 trip, 10 trip
seats, 5 bookings, 5 payments, and 1 waitlist entry. All three reporting views
and both integrity triggers were `VALID`. The restored report returned 10
booked seats, 100% occupancy, ₹8,388 captured, ₹1,398 refunded, and ₹6,990
net. The private dump remained outside Git. See `docs/recovery_drill.md`.

## Later staff dashboard snapshot

A later `/insights/` screenshot on 1 November 2026 showed trip 6 with 6 of 10
seats booked (60% occupancy). The report displayed ₹9,087 simulated captured,
₹4,893 refunded, and ₹4,194 net. These values came from
`V_TRIP_OCCUPANCY` and `V_TRIP_REVENUE` after additional cancellations, so
they differ from the earlier 100% occupancy snapshot above.

The new waiting-list demand panel, sourced from `V_WAITLIST_QUEUE`, displayed
0 waiting passengers and 0 open seat offers, with its empty state visible.
This confirms that the staff page renders the queue view when no active demand
exists. The nonempty case was observed in a later preview below.

The isolated `preview_waitlist_demand` command later created preview trip 22
with one `WAITING` passenger and one unexpired `OFFERED` seat, then removed
its temporary trip, users, bookings, payment, seats, and queue entries after
Enter was pressed. The command output confirms setup and cleanup for that run.

A second preview screenshot showed temporary trip 23, Queue Demo A to Queue
Demo B, with 1 waiting passenger and 1 open offer in the `V_WAITLIST_QUEUE`
dashboard. The demand bar was visible. `V_TRIP_OCCUPANCY` showed 0 of 1 seat
booked, and `V_TRIP_REVENUE` showed ₹100 captured, ₹100 refunded, and ₹0 net
for that cancelled preview booking. The overall dashboard showed 2 trips, 11
seats, 6 booked seats, and ₹4,194 net while the preview trip was present.
The screenshots verify the nonempty view; cleanup of this second run should
be confirmed separately after pressing Enter in the preview command.

## SQL Developer worksheet check

The first run of `docs/live_sql_demo.sql` used the `BUSBOOKING_RESTORE`
connection rather than the live `BUSBOOKING` schema. It showed seven booking
tables, 38 check constraints, seven primary keys, 11 foreign keys, five
unique constraints, and all three views and two triggers `VALID`. Its
restored report showed 10 of 10 seats booked and ₹6,990 net, consistent with
the earlier recovery snapshot. The queue view returned no active rows.
Query 4 raised `ORA-01747` because Oracle requires the seat column named
`NUMBER` to be quoted in this SQL. The worksheet was corrected to
`s."NUMBER"`. A rerun returned all ten Kurnool-to-Vijayawada seat rows for
bus 10901, confirming the four-table join works. A subsequent session query
confirmed `BUSBOOKING_RESTORE` on `xepdb1`; every seat showed `BOOKED`, as
expected from the restore snapshot.
The initial text sort placed seat `10` between `1` and `2`, so the worksheet
now sorts numeric labels numerically while allowing alphanumeric labels.
The latest SQL Developer result still showed the old text order, indicating
the worksheet had not yet been refreshed with the revised `ORDER BY` clause.
