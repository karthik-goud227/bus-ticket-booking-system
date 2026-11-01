# DBMS demonstration path

Use this as a speaking sequence during the live demo. Show actual database
output; do not claim a result that has not been observed.

| Concept | What to show | Current evidence |
| --- | --- | --- |
| Relational design and 3NF | Bus, Seat, Trip, TripSeat, Booking, Payment, WaitlistEntry and their keys | `booking/models.py`, `booking/migrations/0001_initial.py`, `docs/dbms_design.md` |
| Entity integrity | Primary keys, foreign keys, unique registration and `(trip, seat)` | `docs/dbms_evidence.sql` constraint query |
| Domain integrity | Fare, route, time, status, and inventory-state checks | `docs/dbms_evidence.sql` constraint query |
| Cross-table integrity | Wrong bus seat, wrong booking trip, wrong offered trip rejected | Oracle triggers in migration `0003`; `verify_integrity` passed all three ORA-20001/2/3 checks |
| ACID transactions | All selected seats held together or rolled back; payment and status committed together | `booking/services.py`; `verify_atomic_hold` passed twice with failure injected on the second seat |
| Concurrency control | 20 independent sessions compete for one seat; one succeeds | `verify_seat_race` output: 1 success, 19 conflicts, 1 held booking |
| Views and analytic SQL | Occupancy, simulated revenue, FIFO queue position | Migration `0004`; run queries after migration |
| Indexes and optimizer | Trip search and FIFO index definitions, actual execution plans | `docs/query_plans.sql`; do not promise index use on a tiny dataset |
| Recovery | Database backup and restore into a separate schema/database | Pending exercise |

Presentation order: show the ER model and normalization, then constraints and
triggers, then a seat booking in the app, then the race result, then reporting
views and execution plans. Finish with recovery evidence once completed.
