-- Run as BUSBOOKING in SQL Developer. Run each EXPLAIN PLAN followed by DISPLAY.
-- A small database may reasonably choose a full scan. Record the actual plan;
-- do not claim an index speedup without a larger dataset and measurements.

-- Trip search: current live route. Replace cities if your demo data changes.
-- Compare the plan with IDX_TRIP_SEARCH in USER_INDEXES.
EXPLAIN PLAN FOR
SELECT id, origin, destination, departure_at, fare
FROM booking_trip
WHERE origin = 'Kurnool'
  AND destination = 'Vijayawada'
  AND departure_at >= SYSTIMESTAMP
ORDER BY departure_at;

SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());

-- FIFO waiting list: current live trip ID 6. Replace it if the trip changes.
-- Compare the plan with IDX_WAITLIST_FIFO.
EXPLAIN PLAN FOR
SELECT id, user_id, joined_at
FROM booking_waitlistentry
WHERE trip_id = 6 AND status = 'WAITING'
ORDER BY joined_at, id;

SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());
