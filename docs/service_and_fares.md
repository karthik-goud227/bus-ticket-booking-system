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

For new bookings from fare policy version 2, the simulated bill is:

| Component | Rule |
| --- | --- |
| Seat fare | Trip fare × number of selected places |
| Platform fee | ₹20 per booking |
| Service fee | 2% of the seat fare subtotal, rounded to the nearest paisa |
| Illustrative GST | 18% of platform fee plus service fee, rounded to the nearest paisa |
| Total | Sum of all four components |

For example, two seats at ₹499 each have a ₹998 base fare, ₹20 platform fee,
₹19.96 service fee and ₹7.19 illustrative GST, for a ₹1,045.15 total.
One seat at the same fare has a ₹499 base, ₹20 platform fee, ₹9.98 service fee
and ₹5.40 illustrative GST, for a ₹534.38 total. Tax changes with the number
of seats because the service fee changes. The platform fee remains fixed.

The amounts and the fare policy version are stored on Booking at hold time. Confirming creates a Payment
for exactly that total. Cancellation records a simulated refund of the same
amount. The tax example is for a classroom demonstration and is not a claim
about a real operator's current tax treatment.
Migration `0015_bill_integrity` adds Oracle CHECK constraints requiring every
component to be nonnegative and the stored total to equal their sum. Run
`manage.py verify_bill_integrity` after migration to check all saved bills and
prove Oracle rejects a one-paisa mismatch; its probe is rolled back.
Migration `0016_dynamic_fare_policy` gives older bookings version 1 and new
bookings version 2. Oracle checks the version 2 fee and GST formulas in
addition to the total sum. The verifier also probes an incorrect service fee
while leaving the total arithmetically balanced. Existing bookings and
simulated payments are not recalculated or changed.

BusReview has one row per booking. The application accepts a 1–5 star review
only from the booking owner, after a confirmed trip has arrived. Oracle
constraints enforce the rating range and one-to-one booking relationship.
Search results display the average and number of verified reviews.

The footer links to an in-app support desk. Signed-in passengers can create
requests and see their status and staff response. Staff manage requests in
Django admin. No telephone number or external messaging service is implied.

After migrating, check a new booking's bill in SQL Developer:

```sql
SELECT reference, fare_policy_version, base_fare, platform_fee, service_fee, gst_amount,
       total_fare, boarding_point_id, dropoff_point_id
FROM booking_booking
ORDER BY created_at DESC FETCH FIRST 5 ROWS ONLY;
```
