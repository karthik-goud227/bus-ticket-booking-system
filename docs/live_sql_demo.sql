-- BUSBOOKING / XEPDB1: read-only SQL Developer presentation worksheet.
-- Run one numbered query at a time. It does not modify project data.
-- Trip-specific examples below use the observed Kurnool -> Vijayawada route.

-- 1. Prove the session is connected to the project schema and PDB.
SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') AS connected_user,
       SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS service_name
FROM dual;

-- 2. Show the normalized application tables.
SELECT table_name
FROM user_tables
WHERE table_name LIKE 'BOOKING_%'
ORDER BY table_name;

-- 3. Count key and domain rules enforced by Oracle.
SELECT CASE constraint_type
           WHEN 'P' THEN 'PRIMARY KEY'
           WHEN 'R' THEN 'FOREIGN KEY'
           WHEN 'U' THEN 'UNIQUE'
           WHEN 'C' THEN 'CHECK'
           ELSE constraint_type
       END AS rule_type,
       COUNT(*) AS rule_count
FROM user_constraints
WHERE table_name LIKE 'BOOKING_%'
GROUP BY constraint_type
ORDER BY constraint_type;

-- 4. Show the bus -> physical seat -> trip inventory relationship.
SELECT t.id AS trip_id, t.origin, t.destination,
       b.registration_number, s."NUMBER" AS seat_number, ts.status AS seat_status
FROM booking_trip t
JOIN booking_bus b ON b.id = t.bus_id
JOIN booking_tripseat ts ON ts.trip_id = t.id
JOIN booking_seat s ON s.id = ts.seat_id
WHERE t.origin = 'Kurnool' AND t.destination = 'Vijayawada'
ORDER BY t.id,
         CASE WHEN REGEXP_LIKE(s."NUMBER", '^[0-9]+$')
              THEN TO_NUMBER(s."NUMBER") END NULLS LAST,
         s."NUMBER";

-- 5. Read the occupancy and simulated revenue reporting views together.
SELECT o.trip_id, o.origin, o.destination, o.total_seats,
       o.booked_seats, o.available_seats, o.occupancy_pct,
       r.captured_amount, r.refunded_amount, r.net_amount
FROM v_trip_occupancy o
JOIN v_trip_revenue r ON r.trip_id = o.trip_id
ORDER BY o.trip_id;

-- 6. Join passenger bookings to their one-to-one simulated payment records.
SELECT b.reference, u.username, b.status AS booking_status,
       b.total_fare, p.status AS payment_status, p.amount,
       b.created_at, b.confirmed_at, b.cancelled_at, p.refunded_at
FROM booking_booking b
JOIN auth_user u ON u.id = b.user_id
LEFT JOIN booking_payment p ON p.booking_id = b.id
ORDER BY b.created_at DESC
FETCH FIRST 10 ROWS ONLY;

-- 7. Show Oracle's analytic FIFO queue positions. Run while the temporary
-- preview command is paused to see one OFFERED and one WAITING passenger.
SELECT entry_id, trip_id, user_id, status, queue_position, offer_expires_at
FROM v_waitlist_queue
ORDER BY trip_id, queue_position;

-- 8. Verify the three reporting views and two integrity triggers are valid.
SELECT object_type, object_name, status
FROM user_objects
WHERE object_name IN (
    'V_TRIP_OCCUPANCY', 'V_TRIP_REVENUE', 'V_WAITLIST_QUEUE',
    'TRG_TRIPSEAT_SAME_TRIP_BUS', 'TRG_WAITLIST_OFFER_TRIP'
)
ORDER BY object_type, object_name;

-- 9. Show the Oracle function-based unique index for active queue entries.
-- It appears in USER_INDEXES rather than USER_CONSTRAINTS.
SELECT index_name, uniqueness, index_type, status
FROM user_indexes
WHERE index_name = 'UQ_ACTIVE_WAITLIST';

-- 10. Show Oracle-written booking status changes after a new booking is made.
-- Existing bookings from before migration 0006 have no reconstructed history.
SELECT e.id AS event_id, b.reference, e.old_status, e.new_status, e.changed_at
FROM booking_bookingstatusevent e
JOIN booking_booking b ON b.id = e.booking_id
ORDER BY e.changed_at DESC, e.id DESC
FETCH FIRST 10 ROWS ONLY;
