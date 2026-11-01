# SQL Developer live demonstration

Connect as `BUSBOOKING` to `XEPDB1`, then open `docs/live_sql_demo.sql`.
Run one numbered statement at a time. The worksheet only reads data.
If step 1 says `BUSBOOKING_RESTORE`, switch to the `BUSBOOKING` connection
for the live app. The restore schema is an older snapshot and its occupancy,
payment, and queue results can differ.

| Step | What to say while showing the result |
| --- | --- |
| 1. Session | “This is the project schema inside Oracle's pluggable database.” Confirm `BUSBOOKING` and `xepdb1` in the result. |
| 2. Tables | “The business entities are stored separately; trip inventory is one row per physical seat per trip.” |
| 3. Constraints | “Primary, foreign, unique, and check rules reject invalid data at the database boundary.” The `C` category can also include Oracle-generated not-null checks. |
| 4. Joins | “A bus owns physical seats. A trip uses a bus, and `TripSeat` tracks each seat's state on that trip.” This is why a seat can be reused on a later trip. |
| 5. Views | “Oracle calculates live occupancy and simulated net revenue. Cancellation lowers occupancy and records a refund without erasing the booking history.” |
| 6. Payment join | “The payment table is separate and one-to-one with a booking. A cancelled hold has no payment row; a cancelled confirmed booking has a refunded row.” No real payment occurs. |
| 7. Analytic queue | “`ROW_NUMBER()` gives an ordered position per trip. A cancelled seat is offered to the first waiting passenger.” The view may be empty unless a queue is active. |
| 8. Objects | “These views and triggers were created by migrations and are valid Oracle objects.” |

For a nonempty queue, run `manage.py preview_waitlist_demand` in another
PowerShell window, leave it paused, and run step 7 and open `/insights/`.
Capture the results before pressing Enter in PowerShell to remove test data.
The offer lasts 10 minutes.

For transaction and concurrency evidence, show the saved outputs from
`verify_atomic_hold`, `verify_seat_race`, `verify_waitlist_fifo`, and
`verify_waitlist_leave`. These commands created isolated test data and removed
it. Use `docs/query_plans.sql` for the optimizer discussion and
`docs/recovery_drill.md` for the verified Data Pump restore.

Do not describe an execution-plan cost as measured speed or a simulated
payment as a real charge. Historical screenshots in
`docs/observed_dbms_results.md` were taken at different database states.
