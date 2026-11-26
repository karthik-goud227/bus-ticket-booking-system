-- Oracle SQL Developer schema showcase. Connect as BUSBOOKING to XEPDB1.
-- Run one SELECT at a time with Ctrl+Enter. All statements are read-only.
-- The names below are the actual Oracle table names, not illustrative tables.

-- 1. Confirm the schema and list all project entities.
SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') connected_user,
       SYS_CONTEXT('USERENV', 'SERVICE_NAME') service_name
FROM dual;

SELECT table_name
FROM user_tables
WHERE table_name LIKE 'BOOKING_%' OR table_name = 'AUTH_USER'
ORDER BY table_name;

-- 2. Show EVERY column, its Oracle type, and whether NULL is allowed.
-- In SQL Developer, filter TABLE_NAME to focus on one entity at a time.
SELECT table_name, column_id, column_name,
       data_type || CASE
         WHEN data_type IN ('VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR')
           THEN '(' || char_length || ')'
         WHEN data_type = 'NUMBER' AND data_precision IS NOT NULL
           THEN '(' || data_precision || ',' || NVL(data_scale, 0) || ')'
         ELSE '' END data_type,
       nullable
FROM user_tab_columns
WHERE table_name LIKE 'BOOKING_%' OR table_name = 'AUTH_USER'
ORDER BY table_name, column_id;

-- 3. Show primary keys and unique keys, including their key columns.
SELECT c.table_name, c.constraint_name,
       CASE c.constraint_type WHEN 'P' THEN 'PRIMARY KEY'
                              WHEN 'U' THEN 'UNIQUE KEY' END key_type,
       LISTAGG(cc.column_name, ', ') WITHIN GROUP (ORDER BY cc.position) key_columns,
       c.status
FROM user_constraints c
JOIN user_cons_columns cc ON cc.constraint_name = c.constraint_name
                         AND cc.table_name = c.table_name
WHERE c.constraint_type IN ('P', 'U')
  AND (c.table_name LIKE 'BOOKING_%' OR c.table_name = 'AUTH_USER')
GROUP BY c.table_name, c.constraint_name, c.constraint_type, c.status
ORDER BY c.table_name, key_type, c.constraint_name;

-- 4. Show each relationship as CHILD.COLUMN -> PARENT.COLUMN.
SELECT child.table_name child_entity, child_col.column_name foreign_key,
       parent.table_name parent_entity, parent_col.column_name referenced_key,
       child.constraint_name, child.status
FROM user_constraints child
JOIN user_cons_columns child_col
  ON child_col.constraint_name = child.constraint_name
 AND child_col.table_name = child.table_name
JOIN user_constraints parent ON parent.constraint_name = child.r_constraint_name
JOIN user_cons_columns parent_col
  ON parent_col.constraint_name = parent.constraint_name
 AND parent_col.table_name = parent.table_name
 AND parent_col.position = child_col.position
WHERE child.constraint_type = 'R'
  AND child.table_name LIKE 'BOOKING_%'
ORDER BY child.table_name, child.constraint_name, child_col.position;

-- 5. Show CHECK rules and their actual Oracle conditions.
-- Oracle also creates NOT NULL checks, so some rows are routine domain rules.
SELECT table_name, constraint_name, search_condition_vc check_expression, status
FROM user_constraints
WHERE constraint_type = 'C' AND table_name LIKE 'BOOKING_%'
ORDER BY table_name, constraint_name;

-- 6. Show the special conditional unique indexes for waiting-list rules.
-- These are indexes rather than USER_CONSTRAINTS rows.
SELECT index_name, table_name, uniqueness, index_type, status
FROM user_indexes
WHERE index_name IN ('UQ_ACTIVE_WAITLIST', 'UQ_ACTIVE_OFFER_SEAT')
ORDER BY index_name;

-- 7. Show database views and triggers that hold/report project rules.
SELECT object_type, object_name, status
FROM user_objects
WHERE object_type IN ('VIEW', 'TRIGGER')
  AND (object_name LIKE 'V_%' OR object_name LIKE 'TRG_%')
ORDER BY object_type, object_name;

-- 8. Show safe sample rows across the main relationships.
-- Admin accounts and passengers are both AUTH_USER rows; no password hash
-- or private contact number is selected for projection.
SELECT u.id user_id, u.username, u.is_staff, u.is_superuser,
       b.reference, b.status booking_status,
       t.origin, t.destination, t.departure_at,
       bus.registration_number,
       p.status simulated_payment_status
FROM auth_user u
LEFT JOIN booking_booking b ON b.user_id = u.id
LEFT JOIN booking_trip t ON t.id = b.trip_id
LEFT JOIN booking_bus bus ON bus.id = t.bus_id
LEFT JOIN booking_payment p ON p.booking_id = b.id
ORDER BY u.id, b.id DESC FETCH FIRST 25 ROWS ONLY;

-- 9. For real-time changes, create a booking on the website and rerun this.
SELECT b.id, b.reference, b.status, b.created_at,
       t.origin, t.destination, t.departure_at,
       COUNT(ts.id) allocated_seats
FROM booking_booking b
JOIN booking_trip t ON t.id = b.trip_id
LEFT JOIN booking_tripseat ts ON ts.booking_id = b.id
GROUP BY b.id, b.reference, b.status, b.created_at,
         t.origin, t.destination, t.departure_at
ORDER BY b.id DESC FETCH FIRST 10 ROWS ONLY;
