# Oracle backup and restore drill

Completed locally on 1 November 2026 using Oracle Database 21c XE Data Pump.
The source schema was `BUSBOOKING`; the separate restore schema was
`BUSBOOKING_RESTORE`. The working application remained pointed at `BUSBOOKING`.
No dump file or password belongs in Git.

## Export

`SYSTEM` granted `READ, WRITE` on `DATA_PUMP_DIR` to `BUSBOOKING`.
The local Oracle Net alias `BUSBK` pointed to the `xepdb1` service. From
PowerShell, the export command was:

```text
expdp BUSBOOKING@BUSBK SCHEMAS=BUSBOOKING DIRECTORY=DATA_PUMP_DIR DUMPFILE=busbooking_checkpoint_01.dmp LOGFILE=busbooking_export_01.log
```

Data Pump prompted for the database password. The job completed successfully.
The dump stayed in Oracle's server-side `DATA_PUMP_DIR`.

## Import into a separate schema

`SYSTEM` created `BUSBOOKING_RESTORE`, granted `CREATE SESSION`, `CREATE
TABLE`, `CREATE SEQUENCE`, `CREATE VIEW`, `CREATE TRIGGER`, and `CREATE
PROCEDURE`, set unlimited quota on `USERS`, and granted `READ, WRITE` on
`DATA_PUMP_DIR`. The import command was:

```text
impdp BUSBOOKING_RESTORE@BUSBK DIRECTORY=DATA_PUMP_DIR DUMPFILE=busbooking_checkpoint_01.dmp LOGFILE=busbooking_restore_02.log REMAP_SCHEMA=BUSBOOKING:BUSBOOKING_RESTORE TRANSFORM=OID:N
```

Data Pump prompted for the restore account password. The job completed
successfully. An earlier attempt using `SYSTEM` failed at login and did not
import objects; the successful command above used the restore account.

## Verification in BUSBOOKING_RESTORE

| Object | Restored rows |
| --- | ---: |
| `BOOKING_TRIP` | 1 |
| `BOOKING_TRIPSEAT` | 10 |
| `BOOKING_BOOKING` | 5 |
| `BOOKING_PAYMENT` | 5 |
| `BOOKING_WAITLISTENTRY` | 1 |

All three reporting views and both integrity triggers showed `VALID` in
`USER_OBJECTS`. Querying the restored occupancy and revenue views for trip 6
returned 10 total seats, 10 booked, 100% occupancy, ₹8,388 captured, ₹1,398
refunded, and ₹6,990 net.

This verifies that the snapshot's data and database objects were restored into
an independent schema. It is a point-in-time copy; later changes in the working
schema will not appear there unless another export and import is performed.
