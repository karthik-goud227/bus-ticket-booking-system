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
- Oracle row locks and atomic transactions in the booking service.

Run `docs/dbms_evidence.sql` in SQL Developer to inspect the actual database
objects and reporting queries. Keep query output or screenshots as evidence.
The two triggers are introduced by migration `0003_oracle_integrity` and count
as implemented only after that migration succeeds.
