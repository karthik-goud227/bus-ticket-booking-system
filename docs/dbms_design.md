# DBMS design checkpoint

The application stores each bus once and its physical seats in `Seat`.
`Trip` references one bus. `TripSeat` is the seat inventory for a particular trip,
with a unique `(trip, seat)` pair. `Booking` records the passenger, trip,
fare, and lifecycle state. `Payment` records a simulated capture or refund.
`WaitlistEntry` records arrival order and any timed offer.

This separation avoids repeating bus and seat descriptions in every booking.
It also lets one physical seat be sold independently on different trips.

Database rules already implemented:

- Primary and foreign keys for entity relationships.
- Unique keys for bus registration, bus seat number, trip inventory, booking reference, and one payment per booking.
- Check constraints for valid statuses, nonnegative fares, trip times, and inventory state.
- Oracle triggers for cross-table trip, bus, and offered-seat consistency.
- Indexes for trip search, booking history, and FIFO waitlist order.
- A unique Oracle function-based index for one active waiting-list entry per
  passenger and trip. Terminal entries remain as history, so a passenger can
  join again after leaving. This rule also protects writes outside Django.
- An Oracle row trigger writes a separate `BookingStatusEvent` row whenever a
  booking is created or its status changes. The event insert participates in
  the same transaction as the booking change.
- Oracle row locks and atomic transactions in the booking service.

The active-entry rule is an index rather than a `USER_CONSTRAINTS` row. Oracle
indexes the `(trip_id, user_id)` pair only for `WAITING` and `OFFERED` rows;
other statuses produce two null index expressions. Migration `0005` creates
`UQ_ACTIVE_WAITLIST`, and `verify_active_waitlist` checks both duplicate
rejection and rejoining after cancellation with rollback-only test data.

Migration `0006` creates the audit table and `TRG_BOOKING_STATUS_AUDIT`.
The trigger records old status, new status, and Oracle time for every new
booking and actual status transition, including changes made outside Django.
The audit starts at migration time; it cannot reconstruct older transitions.
The read-only inline on each booking's admin page and query 10 of the SQL
worksheet expose the rows. `verify_booking_audit` exercises a hold,
confirmation, and cancellation, then rolls back both the booking and its
audit rows.

Migration `0008` adds two active waiting-list state checks: an `OFFERED` row
must have a seat and expiry time, while a `WAITING` row must have neither.
`UQ_ACTIVE_OFFER_SEAT` is a second function-based unique index that prevents
two live offers for the same trip seat. Historical accepted, expired, and
cancelled entries can still refer to a seat as appropriate. The booking
service also stops new offers for cancelled, departed, or inactive-bus trips.

Trip search filters route and departure fields. Its substring city matching
does not guarantee use of the composite trip-search index.
The optional "seats available only" control uses a correlated `EXISTS`
subquery over `TripSeat`, excluding seats with an active waiting-list offer.
The displayed bookable seat count is then read in one Oracle query through
`V_TRIP_OCCUPANCY` and the seat inventory. Fare sorting is applied in the
database before limiting the page to 50 trips. This keeps filtering accurate
when some earlier trips are full.

Run `docs/dbms_evidence.sql` in SQL Developer to inspect the actual database
objects and reporting queries. Keep query output or screenshots as evidence.
The two triggers are introduced by migration `0003_oracle_integrity` and count
as implemented only after that migration succeeds.
