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

This demonstrates queue order, a timed offer, and seat reuse after
cancellation. Only one waiting passenger was observed in this live scenario;
multiple-person FIFO fairness still needs a separate test before claiming it.

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
