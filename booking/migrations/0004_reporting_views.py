"""Oracle reporting views for occupancy, simulated revenue, and FIFO order."""
from django.db import migrations


OCCUPANCY_VIEW = """
CREATE OR REPLACE VIEW v_trip_occupancy AS
SELECT t.id AS trip_id,
       t.origin,
       t.destination,
       COUNT(ts.id) AS total_seats,
       SUM(CASE WHEN ts.status = 'BOOKED' THEN 1 ELSE 0 END) AS booked_seats,
       SUM(CASE WHEN ts.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_seats,
       NVL(ROUND(100 * SUM(CASE WHEN ts.status = 'BOOKED' THEN 1 ELSE 0 END)
           / NULLIF(COUNT(ts.id), 0), 2), 0) AS occupancy_pct
FROM booking_trip t
LEFT JOIN booking_tripseat ts ON ts.trip_id = t.id
GROUP BY t.id, t.origin, t.destination
"""

REVENUE_VIEW = """
CREATE OR REPLACE VIEW v_trip_revenue AS
SELECT t.id AS trip_id,
       t.origin,
       t.destination,
       NVL(SUM(p.amount), 0) AS captured_amount,
       SUM(CASE WHEN p.status = 'REFUNDED' THEN p.amount ELSE 0 END) AS refunded_amount,
       SUM(CASE WHEN p.status = 'CAPTURED' THEN p.amount ELSE 0 END) AS net_amount
FROM booking_trip t
LEFT JOIN booking_booking b ON b.trip_id = t.id
LEFT JOIN booking_payment p ON p.booking_id = b.id
GROUP BY t.id, t.origin, t.destination
"""

WAITLIST_VIEW = """
CREATE OR REPLACE VIEW v_waitlist_queue AS
SELECT w.id AS entry_id,
       w.trip_id,
       w.user_id,
       w.status,
       w.joined_at,
       w.offer_expires_at,
       ROW_NUMBER() OVER (PARTITION BY w.trip_id ORDER BY w.joined_at, w.id) AS queue_position
FROM booking_waitlistentry w
WHERE w.status IN ('WAITING', 'OFFERED')
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0003_oracle_integrity")]
    operations = [
        migrations.RunSQL([(OCCUPANCY_VIEW, None)], [("DROP VIEW v_trip_occupancy", None)]),
        migrations.RunSQL([(REVENUE_VIEW, None)], [("DROP VIEW v_trip_revenue", None)]),
        migrations.RunSQL([(WAITLIST_VIEW, None)], [("DROP VIEW v_waitlist_queue", None)]),
    ]
