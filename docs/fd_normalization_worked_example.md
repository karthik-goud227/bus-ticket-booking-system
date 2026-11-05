# Functional dependencies and normalization worked example

## 1. Universal relation before decomposition

Consider an imagined flat relation for a seat on a trip:

`R(TRIP_ID, SEAT_ID, BUS_ID, SEAT_NUMBER, SEAT_TYPE, ORIGIN, DEPARTURE_AT, SEAT_STATUS)`

This is a design exercise, not a table stored in Oracle. It intentionally omits other project fields so the dependencies can be checked by hand. Assume each trip uses one bus, each physical seat belongs to one bus, `(BUS_ID, SEAT_NUMBER)` identifies one physical seat, and `(TRIP_ID, SEAT_ID)` identifies one inventory row. The cross-table bus match must also hold.

The nontrivial functional dependencies are:

1. `TRIP_ID → BUS_ID, ORIGIN, DEPARTURE_AT`
2. `SEAT_ID → BUS_ID, SEAT_NUMBER, SEAT_TYPE`
3. `(BUS_ID, SEAT_NUMBER) → SEAT_ID`
4. `(TRIP_ID, SEAT_ID) → SEAT_STATUS`

`SEAT_STATUS` belongs to a **trip-seat pair**. It does not depend on `SEAT_ID` alone: the same seat may be booked on Monday and available on Tuesday.

## 2. Attribute closure and candidate keys

Start with `{TRIP_ID, SEAT_ID}`. Dependency 1 adds `BUS_ID`, `ORIGIN` and `DEPARTURE_AT`. Dependency 2 adds `SEAT_NUMBER` and `SEAT_TYPE`. Dependency 4 adds `SEAT_STATUS`. The closure contains every attribute of `R`, so `(TRIP_ID, SEAT_ID)` is a superkey. Removing either component loses `SEAT_STATUS`, so it is a candidate key.

There is a second business candidate key. From `{TRIP_ID, SEAT_NUMBER}`, dependency 1 supplies `BUS_ID`; dependency 3 then supplies `SEAT_ID`; dependencies 2 and 4 supply the remaining attributes. Neither component alone determines all of `R`, so `(TRIP_ID, SEAT_NUMBER)` is also a candidate key **under the stated same-bus assumption**.

This second key is logical. The implemented Oracle constraint is `UNIQUE(trip_id, seat_id)` on `BOOKING_TRIPSEAT`; `(bus_id, number)` is unique on `BOOKING_SEAT`. An Oracle trigger checks that the trip and physical seat belong to the same bus.

## 3. Canonical cover

Split right-hand sides to single attributes:

```
TRIP_ID → BUS_ID
TRIP_ID → ORIGIN
TRIP_ID → DEPARTURE_AT
SEAT_ID → BUS_ID
SEAT_ID → SEAT_NUMBER
SEAT_ID → SEAT_TYPE
BUS_ID, SEAT_NUMBER → SEAT_ID
TRIP_ID, SEAT_ID → SEAT_STATUS
```

Under these stated dependencies, neither attribute in either two-attribute left-hand side is extraneous. None of the eight singleton-right-hand-side dependencies follows from the other seven. This is a canonical cover; it can be grouped back by common left-hand sides for readability.

## 4. Why the flat relation is decomposed

In `R`, `TRIP_ID → ORIGIN` and `SEAT_ID → SEAT_TYPE` have determinants that are not superkeys. Those facts repeat for every trip seat and cause update anomalies. The application stores them separately:

| Relation | Key | Facts kept there |
| --- | --- | --- |
| `BOOKING_TRIP` | `id` | Bus, route, departure, arrival and fare for one trip |
| `BOOKING_SEAT` | `id`; alternate `(bus_id, number)` | Physical seat number, type and deck |
| `BOOKING_TRIPSEAT` | `id`; alternate `(trip_id, seat_id)` | Availability, hold expiry and optional booking for one seat on one trip |

`BOOKING_BUS` holds the bus registration, operator label and layout. The foreign keys let Oracle join these relations back for the seat map. Joining `TripSeat` to `Trip` on the trip primary key and to `Seat` on the seat primary key does not create spurious trip-seat pairs. The same-bus relationship is a cross-table business rule, so `TRG_TRIPSEAT_SAME_TRIP_BUS` checks it.

The three projected relations above satisfy BCNF with respect to the listed FDs: each listed nontrivial determinant inside a relation is a key. That statement is limited to the documented dependencies. The full project stores deliberate snapshots, such as booking bill components, because a historical booking must keep the amount charged even if a future trip fare changes. Oracle checks the stored bill arithmetic.

## 5. Scope of higher normal forms

4NF requires a meaningful independent multivalued dependency. The current model does not have an evidenced example such as independent sets of bus amenities and spoken languages. Introducing such columns solely to claim 4NF would weaken the design. Likewise, no nontrivial join dependency in the present requirements justifies a 5NF decomposition. These concepts can be explained as design checks for future feature growth, without claiming that the application implements extra relations.
