# Entity–relationship model and normalization

This diagram reflects the implemented Django models and Oracle tables. A
nullable relationship is shown with a circle. `AUTH_USER` is Django's user
table; the other entities belong to the booking application.

```mermaid
erDiagram
    AUTH_USER ||--o{ BOOKING : makes
    AUTH_USER ||--o{ WAITLIST_ENTRY : joins
    BUS ||--o{ SEAT : contains
    BUS ||--o{ TRIP : operates
    TRIP ||--o{ TRIP_SEAT : inventories
    SEAT ||--o{ TRIP_SEAT : appears_on
    TRIP ||--o{ BOOKING : receives
    TRIP ||--o{ WAITLIST_ENTRY : queues
    BOOKING |o--o{ TRIP_SEAT : allocates
    BOOKING ||--o| PAYMENT : records
    TRIP_SEAT |o--o{ WAITLIST_ENTRY : offered_to

    BUS {
        int id PK
        string registration_number UK
        string operator_name
        string bus_type
    }
    SEAT {
        int id PK
        int bus_id FK
        string number
        string seat_type
    }
    TRIP {
        int id PK
        int bus_id FK
        string origin
        string destination
        datetime departure_at
        datetime arrival_at
        decimal fare
    }
    TRIP_SEAT {
        int id PK
        int trip_id FK
        int seat_id FK
        int booking_id FK
        string status
        datetime hold_expires_at
    }
    AUTH_USER {
        int id PK
        string username UK
    }
    BOOKING {
        int id PK
        int user_id FK
        int trip_id FK
        string reference UK
        string status
        decimal total_fare
    }
    PAYMENT {
        int id PK
        int booking_id FK,UK
        decimal amount
        string status
    }
    WAITLIST_ENTRY {
        int id PK
        int trip_id FK
        int user_id FK
        int offered_seat_id FK
        string status
        datetime joined_at
        datetime offer_expires_at
    }
```

## Why these tables are separate

The candidate key for a physical seat is `(bus_id, number)`. The candidate key
for seat inventory is `(trip_id, seat_id)`. A bus seat can therefore appear on
many trips while each trip has only one inventory row for that physical seat.
`booking_id` in `TRIP_SEAT` is nullable: an available seat has no owner. A
booking can own several seats, but the Oracle trigger ensures its trip matches
every allocated inventory row. Another trigger checks that the physical seat
belongs to the trip's bus.

## Normalization argument

1. **First normal form:** Each column stores one value. Seats selected for a
   booking are separate `TRIP_SEAT` rows rather than a comma-separated seat
   list in `BOOKING`.
2. **Second normal form:** The logical composite keys `(bus_id, number)` and
   `(trip_id, seat_id)` determine facts about one seat or one trip-seat pair.
   Bus details are stored in `BUS`, trip details in `TRIP`, and inventory state
   in `TRIP_SEAT`, avoiding partial dependency on either side of the pair.
3. **Third normal form:** Descriptive facts about the bus, trip, user, and
   payment are stored with their own entity rather than copied into every
   booking or inventory row. Foreign keys connect the entities. For example,
   a booking stores `trip_id` instead of repeating origin, destination, and
   departure time.

Two values are deliberate snapshots rather than a claim of strict derivation:
`BOOKING.total_fare` preserves the price charged when the booking was made,
even if the trip fare changes later. `TRIP_SEAT.status` is stored for direct
inventory locking and must agree with its nullable booking and hold deadline;
the `CK_INVENTORY_STATE` check constraint enforces those combinations.

`BUS.operator_name` is currently a label for each bus. If the project later
needs operator-level accounts, contacts, or policies, move operators into a
separate `OPERATOR` table and reference it from `BUS`. This is a future
normalization extension, not an implemented table.
