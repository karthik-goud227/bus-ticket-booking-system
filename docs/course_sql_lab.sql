-- CS302/AD302 SQL lab for the BUSBOOKING schema in XEPDB1.
-- Run as BUSBOOKING in SQL Developer. No application table is changed.
-- EXPLAIN PLAN may write plan rows to Oracle's PLAN_TABLE.
-- Results reflect the database contents at the time of execution.
-- Oracle 21c uses MINUS for relational difference (EXCEPT in the lecture plan).

-- 1. Selection and projection: future, active trips.
-- Relational algebra: pi[id, origin, destination, departure_at]
--                   (sigma[departure_at > now AND not cancelled](TRIP))
SELECT t.id, t.origin, t.destination, t.departure_at
FROM booking_trip t
WHERE t.departure_at > SYSTIMESTAMP AND t.is_cancelled = 0
ORDER BY t.departure_at
FETCH FIRST 20 ROWS ONLY;

-- 2. Join: a physical seat and its status on a specific trip.
-- The joins follow TripSeat.trip_id and TripSeat.seat_id foreign keys.
SELECT t.id AS trip_id, t.origin, t.destination,
       b.registration_number, s."NUMBER" AS seat_number,
       s.deck, s.seat_type, ts.status AS inventory_status
FROM booking_tripseat ts
JOIN booking_trip t ON t.id = ts.trip_id
JOIN booking_bus b ON b.id = t.bus_id
JOIN booking_seat s ON s.id = ts.seat_id
ORDER BY t.id, s."NUMBER"
FETCH FIRST 30 ROWS ONLY;

-- 3. UNION: passengers who have booked or joined a waiting list.
SELECT user_id FROM booking_booking
UNION
SELECT user_id FROM booking_waitlistentry
ORDER BY user_id;

-- 4. INTERSECT: passengers who have both a booking and a queue entry.
SELECT user_id FROM booking_booking
INTERSECT
SELECT user_id FROM booking_waitlistentry
ORDER BY user_id;

-- 5. Difference: booked passengers who never joined a waiting list.
SELECT user_id FROM booking_booking
MINUS
SELECT user_id FROM booking_waitlistentry
ORDER BY user_id;

-- 6. Correlated EXISTS: trips with at least one available inventory row.
SELECT t.id, t.origin, t.destination, t.departure_at
FROM booking_trip t
WHERE t.is_cancelled = 0
  AND EXISTS (
      SELECT 1 FROM booking_tripseat ts
      WHERE ts.trip_id = t.id AND ts.status = 'AVAILABLE'
  )
ORDER BY t.departure_at
FETCH FIRST 20 ROWS ONLY;

-- 7. Aggregation and HAVING: trips with at least one confirmed booking.
SELECT t.id AS trip_id, t.origin, t.destination,
       COUNT(b.id) AS confirmed_bookings,
       SUM(b.total_fare) AS confirmed_bill_total
FROM booking_trip t
JOIN booking_booking b ON b.trip_id = t.id
WHERE b.status = 'CONFIRMED'
GROUP BY t.id, t.origin, t.destination
HAVING COUNT(b.id) >= 1
ORDER BY t.id;

-- 8. NULL and outer join: held bookings with no payment row yet.
SELECT b.reference, b.status, b.hold_expires_at
FROM booking_booking b
LEFT JOIN booking_payment p ON p.booking_id = b.id
WHERE b.status = 'HELD' AND p.id IS NULL
ORDER BY b.created_at DESC;

-- 9. Universal quantification with NOT EXISTS: trips with inventory but
-- no currently AVAILABLE rows. This includes held and booked inventory.
SELECT t.id, t.origin, t.destination
FROM booking_trip t
WHERE EXISTS (
    SELECT 1 FROM booking_tripseat ts WHERE ts.trip_id = t.id
)
AND NOT EXISTS (
    SELECT 1 FROM booking_tripseat ts
    WHERE ts.trip_id = t.id AND ts.status = 'AVAILABLE'
)
ORDER BY t.id;

-- 10. Compare the stored reporting definition with direct inventory counts.
SELECT v.trip_id, v.total_seats, v.booked_seats, v.available_seats,
       COUNT(ts.id) AS joined_inventory_rows
FROM v_trip_occupancy v
LEFT JOIN booking_tripseat ts ON ts.trip_id = v.trip_id
GROUP BY v.trip_id, v.total_seats, v.booked_seats, v.available_seats
ORDER BY v.trip_id;

-- 11. Oracle metadata: implemented keys and referential constraints.
SELECT c.table_name, c.constraint_name, c.constraint_type,
       LISTAGG(cc.column_name, ', ') WITHIN GROUP (ORDER BY cc.position) AS columns_in_key
FROM user_constraints c
JOIN user_cons_columns cc ON cc.constraint_name = c.constraint_name
WHERE c.table_name IN ('BOOKING_BUS', 'BOOKING_SEAT', 'BOOKING_TRIP',
                       'BOOKING_TRIPSEAT', 'BOOKING_BOOKING', 'BOOKING_PAYMENT')
  AND c.constraint_type IN ('P', 'U', 'R')
GROUP BY c.table_name, c.constraint_name, c.constraint_type
ORDER BY c.table_name, c.constraint_type, c.constraint_name;

-- 12. Optimizer exercise. Inspect the actual plan; do not infer speed from it.
-- Change the route literals when presenting a different dataset.
EXPLAIN PLAN FOR
SELECT t.id, t.departure_at, t.fare
FROM booking_trip t
WHERE t.origin = 'Kurnool' AND t.destination = 'Vijayawada'
  AND t.departure_at >= SYSTIMESTAMP
ORDER BY t.departure_at;

SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());
