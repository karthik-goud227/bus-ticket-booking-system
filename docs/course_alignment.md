# DBMS lecture plan alignment

This map relates the IIITDM Kurnool CS302/AD302 lecture plan to the BusBook implementation. It separates features enforced by Oracle, concepts demonstrated with SQL, and topics that remain theory or future work. The accompanying `course_sql_lab.sql` uses the actual `BUSBOOKING` schema without changing application tables. Its `EXPLAIN PLAN` command may write to Oracle's plan table.

| Module | Course topic | Evidence in this project | Status |
| --- | --- | --- | --- |
| 1 | DBMS architecture and data models | Browser, Django views and services, ORM, Oracle XE; persistent tables and transactions | Implemented |
| 2 | ER model, relational mapping and integrity | `Bus`, `Seat`, `Trip`, `TripSeat`, `Booking`, `WaitlistEntry`, keys, foreign keys and checks | Implemented; see `er_model.md` |
| 3 | SQL selection, projection, joins, set operations, nested queries, aggregates and NULL | Queries 1–9 in `course_sql_lab.sql` | Demonstration worksheet; results depend on current data |
| 3 | Complex constraints and triggers | Oracle seat/bus, offer/trip and trip overlap guards; booking status audit trigger; function-based unique indexes | Implemented and probed |
| 4 | FD closure, candidate keys, canonical cover and decomposition | Worked universal-relation example in `fd_normalization_worked_example.md` | Formal design explanation |
| 4 | 1NF, 2NF, 3NF and BCNF | Separate trip, seat and per-trip inventory relations; documented snapshot fields | Design analysis, with stated assumptions |
| 4 | Multivalued dependencies, 4NF and 5NF | No independent multivalued attribute sets or join dependency are established by the present requirements | Theory boundary; no artificial implementation claim |
| 5 | ACID, locking, concurrent schedules and recoverability | `transaction.atomic()`, `SELECT FOR UPDATE`, rollback and 20-session seat race | Implemented and verified; does not prove global serializable isolation |
| 5 | Deadlocks and non-locking concurrency | Stable lock order helps reduce contention; Oracle manages locks | No dedicated deadlock or optimistic-concurrency experiment yet |
| 6 | Query evaluation and optimization | `IDX_TRIP_SEARCH`, `IDX_WAITLIST_FIFO`, `EXPLAIN PLAN` and `DBMS_XPLAN` | Actual plans can be inspected; no speedup claim on small data |
| 7 | Recovery | Oracle Data Pump export and remapped restore, plus atomic rollback probes | Restore drill verified; internal redo/undo mechanisms are explained conceptually |
| 7 | Security and authorization | Passenger ownership checks, staff-only views, Django authentication, Oracle schema account | Implemented at app level; production-grade least privilege needs separate deployment work |

## Best presentation emphasis

1. **ER and schema design:** Explain why `TripSeat` is a separate relation. A physical seat persists across trips, while status belongs to one seat on one trip.
2. **Keys and FDs:** Show the two business candidate keys `(bus_id, number)` and `(trip_id, seat_id)`, then derive the latter's attribute closure in the worked example.
3. **Database-enforced integrity:** Distinguish row-level `CHECK` rules from cross-table rules requiring Oracle triggers. Include the one-paisa billing rejection as a successful constraint probe.
4. **Transactions:** Explain the lock and commit path, the 20-session race result, and the all-or-nothing second-seat failure.
5. **SQL and optimization:** Run a few worksheet queries in SQL Developer and show the actual `DBMS_XPLAN` output. Small tables can legitimately use full scans.

## Evidence limits

The SQL worksheet has been reviewed against the current model and migration definitions, but has not yet been run against the live Oracle service in this milestone. Its results depend on the live data. The functional-dependency example describes the projected business attributes of the current schema, not an extra physical table. The project does not implement a payment gateway; amounts and refunds are simulated.
