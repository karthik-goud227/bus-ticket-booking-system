-- Run in SQL Developer while connected as BUSBOOKING.
-- These are inspection and report queries. They do not modify project data.

-- 1. Relational tables created by Django migrations.
SELECT table_name
FROM user_tables
WHERE table_name LIKE 'BOOKING_%'
ORDER BY table_name;

-- 2. Primary, foreign, unique, and check constraints.
SELECT table_name, constraint_name, constraint_type, status
FROM user_constraints
WHERE table_name LIKE 'BOOKING_%'
ORDER BY table_name, constraint_type, constraint_name;

-- 3. Indexes used for trip search, booking history, and FIFO queue.
SELECT index_name, table_name, uniqueness, status
FROM user_indexes
WHERE table_name LIKE 'BOOKING_%'
ORDER BY table_name, index_name;

-- 4. Oracle triggers enforcing cross-table business rules.
SELECT trigger_name, table_name, status
FROM user_triggers
WHERE trigger_name IN ('TRG_TRIPSEAT_SAME_TRIP_BUS', 'TRG_WAITLIST_OFFER_TRIP')
ORDER BY trigger_name;

-- Both trigger objects must say VALID. If not, inspect USER_ERRORS.
SELECT object_name, status
FROM user_objects
WHERE object_type = 'TRIGGER'
  AND object_name IN ('TRG_TRIPSEAT_SAME_TRIP_BUS', 'TRG_WAITLIST_OFFER_TRIP')
ORDER BY object_name;

SELECT name, line, position, text
FROM user_errors
WHERE type = 'TRIGGER'
  AND name IN ('TRG_TRIPSEAT_SAME_TRIP_BUS', 'TRG_WAITLIST_OFFER_TRIP')
ORDER BY name, sequence;

-- 4b. Reporting views; all should be VALID after migration 0004.
SELECT object_name, status
FROM user_objects
WHERE object_type = 'VIEW'
  AND object_name IN ('V_TRIP_OCCUPANCY', 'V_TRIP_REVENUE', 'V_WAITLIST_QUEUE')
ORDER BY object_name;

SELECT * FROM v_trip_occupancy ORDER BY trip_id;
SELECT * FROM v_trip_revenue ORDER BY trip_id;
SELECT * FROM v_waitlist_queue ORDER BY trip_id, queue_position;

-- 5. Trip occupancy, including empty trips.
SELECT t.id AS trip_id, t.origin, t.destination,
       COUNT(ts.id) AS total_seats,
       SUM(CASE WHEN ts.status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_seats,
       SUM(CASE WHEN ts.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_seats
FROM booking_trip t
LEFT JOIN booking_tripseat ts ON ts.trip_id = t.id
GROUP BY t.id, t.origin, t.destination
ORDER BY t.id;

-- 6. Captured and refunded simulated payment totals.
SELECT status, COUNT(*) AS payment_count, SUM(amount) AS total_amount
FROM booking_payment
GROUP BY status
ORDER BY status;

-- 7. Waiting-list order for each trip.
SELECT trip_id, user_id, status, joined_at,
       ROW_NUMBER() OVER (PARTITION BY trip_id ORDER BY joined_at, id) AS queue_position
FROM booking_waitlistentry
WHERE status IN ('WAITING', 'OFFERED')
ORDER BY trip_id, queue_position;
