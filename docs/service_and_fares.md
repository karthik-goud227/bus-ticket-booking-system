# Service, journey points, reviews, and fare policy

Migration `0013_service_billing_reviews` creates TripPoint, BusReview, and
SupportRequest tables. It adds boarding/drop-off references and a saved fare
breakdown to Booking. Existing trips receive their origin and destination bus
stands as default points. Existing bookings retain their original total as
the base fare; no new fees are added to old records.

Staff can add additional timed boarding and drop-off points in Django admin.
The point time must fall within the trip interval. A booking validates that
the selected boarding and drop-off points belong to its trip and occur in
the correct order. Each new trip automatically receives default city points.

For new bookings, the simulated bill is:

| Component | Rule |
| --- | --- |
| Seat fare | Trip fare × number of selected places |
| Platform fee | ₹20 per booking |
| Service fee | ₹10 per booking |
| Illustrative GST | 18% of the two fees = ₹5.40 |
| Total | Sum of all four components |

The amounts are stored on Booking at hold time. Confirming creates a Payment
for exactly that total. Cancellation records a simulated refund of the same
amount. The tax example is for a classroom demonstration and is not a claim
about a real operator's current tax treatment.

BusReview has one row per booking. The application accepts a 1–5 star review
only from the booking owner, after a confirmed trip has arrived. Oracle
constraints enforce the rating range and one-to-one booking relationship.
Search results display the average and number of verified reviews.

The footer links to an in-app support desk. Signed-in passengers can create
requests and see their status and staff response. Staff manage requests in
Django admin. No telephone number or external messaging service is implied.

After migrating, check a new booking's bill in SQL Developer:

```sql
SELECT reference, base_fare, platform_fee, service_fee, gst_amount,
       total_fare, boarding_point_id, dropoff_point_id
FROM booking_booking
ORDER BY created_at DESC FETCH FIRST 5 ROWS ONLY;
```
