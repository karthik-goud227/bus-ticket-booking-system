# DBMS demonstration path

Use this as a speaking sequence during the live demo. Show actual database
output; do not claim a result that has not been observed.
For a compact SQL Developer walkthrough, use `docs/live_sql_demo.sql` with
the speaking notes in `docs/live_sql_demo.md`.

| Concept | What to show | Current evidence |
| --- | --- | --- |
| Relational design and 3NF | Bus, Seat, Trip, TripSeat, Booking, Payment, WaitlistEntry and their keys | `docs/er_model.md`, `booking/models.py`, `booking/migrations/0001_initial.py` |
| Entity integrity | Primary keys, foreign keys, unique registration and `(trip, seat)` | `docs/dbms_evidence.sql` constraint query |
| Domain integrity | Fare, route, time, status, and inventory-state checks | `docs/dbms_evidence.sql` constraint query |
| Cross-table integrity | Wrong bus seat, wrong booking trip, wrong offered trip rejected | Oracle triggers in migration `0003`; `verify_integrity` passed all three ORA-20001/2/3 checks |
| ACID transactions | All selected seats held together or rolled back; payment and status committed together | `booking/services.py`; `verify_atomic_hold` passed twice with failure injected on the second seat |
| Booking lifecycle and payment join | Open a confirmed and a cancelled booking; compare hold, confirmation, cancellation, capture, and refund timestamps | Passenger booking activity panel reads `Booking` and its related `Payment` row |
| Concurrency control | 20 independent sessions compete for one seat; one succeeds | `verify_seat_race` output: 1 success, 19 conflicts, 1 held booking |
| FIFO queue and offer expiry | Two waiting passengers, cancellation, first offer expiry, second offer confirmation | `verify_waitlist_fifo` passed all three checks and removed its test rows |
| Passenger queue position and exit | Show `v_waitlist_queue` positions in My bookings; leaving an offer passes it to the next passenger | `verify_waitlist_leave` passed all three checks and removed its test rows |
| Views and analytic SQL | Occupancy, simulated revenue, FIFO queue position | Migration `0004`; run queries after migration |
| Live queue demand | Staff Insights groups waiting passengers and unexpired offers by trip | `V_WAITLIST_QUEUE` feeds the dashboard; use `preview_waitlist_demand` to show an isolated nonempty chart, then press Enter to clean up |
| Indexes and optimizer | Trip search and FIFO index definitions, actual execution plans | `docs/query_plans.sql`; do not promise index use on a tiny dataset |
| Recovery | Data Pump export from `BUSBOOKING`, import into `BUSBOOKING_RESTORE`, row and object checks | `docs/recovery_drill.md`; 5 object types counted, three views and two triggers `VALID` |

Presentation order: show the ER model and normalization, then constraints and
triggers, then a seat booking in the app, then the race result, then reporting
views and execution plans. Finish with recovery evidence once completed.
