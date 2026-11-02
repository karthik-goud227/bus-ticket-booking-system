# Install and run on another computer

These instructions are for a **fresh Windows computer running its own copy**.
That computer gets its own Oracle schema and its own data. To use the project
already running on a teammate's laptop, follow [team access](team_access.md)
instead; only a browser is needed in that case.

## What each computer needs

| Role | Install | Data location |
| --- | --- | --- |
| App host (your own copy) | Windows, Oracle Database 21c XE with `xepdb1`, Python 3.14, browser; SQL Developer is useful for DBMS demonstrations | Local Oracle `BUSBOOKING` schema |
| Teammate opening a shared app | Browser and connection to the host's Wi-Fi/hotspot | Host laptop's Oracle database |
| Code contributor | Git, plus host requirements if running a separate copy | Their own schema unless they use a shared host |

The repository contains Django code, migrations, templates and CSS. It does
**not** contain Oracle Database, Python, an already populated database, or
passwords. `requirements.txt` pins Django and `oracledb`. The setup below is
for Windows PowerShell; `start_team.ps1` uses Windows network commands. WSL2
is optional for Git and is not needed to run this Windows installation.

## 1. Obtain the source

With Git installed and internet available:

```powershell
git clone https://github.com/karthik-goud227/bus-ticket-booking-system.git
cd bus-ticket-booking-system
```

Alternatively, use GitHub's **Code → Download ZIP**, extract it, and open
PowerShell in the extracted project folder. ZIP users can run the app but do
not have Git history or a configured remote for pushing changes. If the
repository is private, its owner must grant access first.

## 2. Prepare Oracle

Install Oracle Database 21c XE and confirm the database and listener services
are running. In SQL Developer, connect to the **`xepdb1` service** as an
administrator, then create a separate project schema. Use a new private
password in place of the example:

```sql
CREATE USER BUSBOOKING IDENTIFIED BY "ChooseYourOwnPassword";
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE,
      CREATE VIEW, CREATE TRIGGER, CREATE PROCEDURE TO BUSBOOKING;
ALTER USER BUSBOOKING QUOTA UNLIMITED ON USERS;
```

Create and test a SQL Developer connection with username `BUSBOOKING`, host
`localhost`, port `1521`, and **service name** `xepdb1`. Do this in the
pluggable database, not the XE root container. Use the `BUSBOOKING` account
for Django; do not use `SYSTEM`. If `BUSBOOKING` already exists on your own
computer, use that account and do not run `CREATE USER` again.

## 3. Install Python packages and create the database tables

From the project folder in Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$secure = Read-Host "BUSBOOKING password" -AsSecureString
$env:DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secure).Password
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Choose a **Django superuser** username and password at the last prompt. This
is a website login, separate from the Oracle `BUSBOOKING` password. `migrate`
creates the project tables, indexes, constraints, Oracle triggers and views.
You do not need to execute migration SQL manually. The database begins with
no buses or trips; add your own in `/admin/`. Optional sample data can be
created with `manage.py seed_demo` after setting `DB_PASSWORD`.
For a broader example, `manage.py seed_fleet` defines 12 buses of varied
types, their seats, and 32 non-overlapping future trips. Run it after
`migrate`, or add buses and trips yourself in admin.
The [fleet schedule guide](fleet_schedule.md) explains the non-overlap rule.

The password variable applies only to the current PowerShell window. Set it
again in every new window used for database commands. `.env.example` lists
supported variables but is **not automatically loaded**. Never commit `.env`,
real passwords, dumps or `.venv` to Git. If your Oracle service is elsewhere,
set `DB_DSN` before the Django command (default `localhost:1521/xepdb1`);
`DB_USER` defaults to `BUSBOOKING`.

## 4. Choose how to open the app

### One computer, with or without internet

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. This uses Oracle and Django on that computer.
No internet is needed after the software and packages have been installed.
The server window must stay open.

### Share with devices on the same Wi-Fi or phone hotspot

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_team.ps1
```

The launcher requests the Oracle password (unless `DB_PASSWORD` is already
set), detects active local IPv4 addresses, starts Django, and prints links
such as `http://192.168.1.10:8000/`. Other devices join the **same network**
and open the matching link. The network may have internet (college Wi-Fi) or
have no internet (a hotspot with mobile data disabled); the booking functions
work either way. Keep Oracle, the host laptop and the server running. Windows
Firewall may need Python allowed on **Private networks**. A college network
may block device-to-device traffic; a shared hotspot is a useful fallback.

After changing networks, press Ctrl+C and run the launcher again. Share the
new link because the host IP can change. Accounts and bookings remain in the
host Oracle database. If a direct `.\start_team.ps1` call is blocked by
PowerShell execution policy, use the `powershell -ExecutionPolicy Bypass`
command above; it applies only to that launched PowerShell process.

### Access from anywhere on the public internet

**Not configured in this repository.** A GitHub repository stores source
code; it does not host this Django app or its Oracle database. The development
server, `DEBUG=True`, default development secret key and HTTP local links are
for classroom testing. Public hosting would require separate infrastructure,
a production server, HTTPS, secure settings and database access. Do not use
router port forwarding as a shortcut to expose this development app.

## 5. Try the main workflow

1. Sign in at `/admin/` with the Django superuser. Add a bus with seats, then
   a future trip using that bus.
2. Visit `/signup/` to create a separate passenger account. Search for the
   trip, hold seats and confirm a **simulated** payment.
3. Open **My bookings** to inspect or print the ticket. Cancel a booking to
   release its seats and record a simulated refund.
4. Fill a trip, create another passenger, join the waiting list, cancel a
   seat and accept the timed offer. Staff can inspect `/insights/`.

Each fresh installation has its own database. Cloning code does **not** copy
the original team's bookings or users. [ER design](er_model.md),
[DBMS demonstration](dbms_demo_path.md), and [read-only SQL walkthrough](live_sql_demo.md)
explain the database behavior.

## Common setup problems

| Symptom | Check |
| --- | --- |
| `ORA-01017` | Re-enter the `BUSBOOKING` password in this PowerShell window; verify the account and `xepdb1` service in SQL Developer. |
| `ORA-12541` or connection refused | Start the Oracle database and listener services; check host, port and service. |
| `ORA-00942` | Confirm migrations succeeded and SQL Developer is connected as `BUSBOOKING` in `xepdb1`. |
| `py -3.14` not found | Install Python 3.14, then create the virtual environment again. |
| Teammate link does not load | Check same network, current printed IP, server window and Private-network firewall access; try a hotspot if college Wi-Fi isolates devices. |
| Port 8000 already in use | Stop the earlier Django server with Ctrl+C before starting another. |

## Offline preparation and GitHub

Internet is normally needed to download Oracle/Python installers, clone the
repository, install Python packages and push to GitHub. Prepare those before
an offline demonstration. On a connected Windows computer using the same
Python version and architecture, Python wheels can be downloaded ahead of
time with `py -3.14 -m pip download -r requirements.txt -d wheelhouse`; then
install from that folder with
`.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements.txt`.
Keep `wheelhouse` out of Git. Git commits can be made offline and pushed after
internet returns. The app's booking and Oracle reporting operations do not
depend on GitHub or a live internet connection.
