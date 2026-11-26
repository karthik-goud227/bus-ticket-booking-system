-- Live Oracle demo. Connect to XEPDB1 as BUSBOOKING in SQL Developer.
-- Run one numbered SELECT at a time with Ctrl+Enter. These queries do not change data.
-- Refresh or rerun after each action in the website.

-- 1. Show the real application tables and row counts.
SELECT 'USERS' entity, COUNT(*) rows_stored FROM auth_user
UNION ALL SELECT 'BUSES', COUNT(*) FROM booking_bus
UNION ALL SELECT 'SEATS', COUNT(*) FROM booking_seat
UNION ALL SELECT 'TRIPS', COUNT(*) FROM booking_trip
UNION ALL SELECT 'TRIP_SEATS', COUNT(*) FROM booking_tripseat
UNION ALL SELECT 'BOOKINGS', COUNT(*) FROM booking_booking
UNION ALL SELECT 'PAYMENTS', COUNT(*) FROM booking_payment
UNION ALL SELECT 'WAITLIST', COUNT(*) FROM booking_waitlistentry;

-- 2. Admin and passenger accounts use AUTH_USER; the staff flags identify admins.
-- Avoid projecting password hashes or private contact details during the demo.
SELECT id, username, is_staff, is_superuser, is_active, date_joined
FROM auth_user ORDER BY id DESC FETCH FIRST 15 ROWS ONLY;

-- 3. Database-enforced foreign keys: R = referential constraint.
SELECT c.table_name child_table, c.constraint_name,
       cc.column_name child_column, p.table_name parent_table,
       pc.column_name parent_column
FROM user_constraints c
JOIN user_cons_columns cc ON cc.constraint_name = c.constraint_name
JOIN user_constraints p ON p.constraint_name = c.r_constraint_name
JOIN user_cons_columns pc ON pc.constraint_name = p.constraint_name
                         AND pc.position = cc.position
WHERE c.constraint_type = 'R'
  AND c.table_name IN ('BOOKING_BOOKING', 'BOOKING_TRIP',
                       'BOOKING_TRIPSEAT', 'BOOKING_PAYMENT')
ORDER BY c.table_name, c.constraint_name, cc.position;

-- 4. A booking joins the passenger, journey, bus, and payment record.
-- Create/confirm/cancel a booking in the site, then rerun this query.
SELECT b.id booking_id, b.reference, u.username passenger,
       t.origin, t.destination, t.departure_at, t.arrival_at,
       bus.registration_number, bus.operator_name,
       b.status booking_status, b.total_fare,
       p.status payment_status
FROM booking_booking b
JOIN auth_user u ON u.id = b.user_id
JOIN booking_trip t ON t.id = b.trip_id
JOIN booking_bus bus ON bus.id = t.bus_id
LEFT JOIN booking_payment p ON p.booking_id = b.id
ORDER BY b.id DESC FETCH FIRST 15 ROWS ONLY;

-- 5. Physical seat -> trip inventory -> booking. Filter by a trip ID if needed.
SELECT t.id trip_id, t.origin, t.destination,
       s.number seat_number, s.deck, s.seat_type,
       ts.status seat_status, b.reference booking_reference
FROM booking_tripseat ts
JOIN booking_trip t ON t.id = ts.trip_id
JOIN booking_seat s ON s.id = ts.seat_id
LEFT JOIN booking_booking b ON b.id = ts.booking_id
ORDER BY t.id DESC, s.number FETCH FIRST 40 ROWS ONLY;

-- 6. Oracle trigger-generated lifecycle history; newest events first.
SELECT e.id event_id, b.reference, e.old_status, e.new_status, e.changed_at
FROM booking_bookingstatusevent e
JOIN booking_booking b ON b.id = e.booking_id
ORDER BY e.id DESC FETCH FIRST 15 ROWS ONLY;

-- 7. Stored account, fleet, and schedule relationships.
SELECT t.id trip_id, bus.registration_number, bus.bus_type,
       t.origin, t.destination, t.departure_at, t.arrival_at,
       t.schedule_id recurring_template_id
FROM booking_trip t
JOIN booking_bus bus ON bus.id = t.bus_id
ORDER BY t.departure_at DESC FETCH FIRST 15 ROWS ONLY;

-- 8. Database reporting views update after booking and cancellation.
SELECT * FROM v_trip_occupancy ORDER BY trip_id DESC FETCH FIRST 15 ROWS ONLY;
SELECT * FROM v_trip_revenue ORDER BY trip_id DESC FETCH FIRST 15 ROWS ONLY;
