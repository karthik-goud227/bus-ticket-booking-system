# Team access and simple GitHub workflow

## One shared app for the three of you

The project leader runs Oracle and Django on their Windows laptop. Teammates
open the site in a browser on the same trusted Wi-Fi or mobile hotspot. They do
not need Oracle, Python, SQL Developer, or Git just to test the shared app.
Keep the host laptop and the server PowerShell window running during testing.
This is a local classroom demonstration, not public internet hosting.

On the host laptop, open PowerShell in the project folder and run:

```powershell
.\start_team.ps1
```

The script asks for the database password and prints the current teammate
link(s). Teammates join the same Wi-Fi or hotspot and open the matching link.
The leader can continue using `http://127.0.0.1:8000/`. Switching between
college Wi-Fi and a hotspot may change the link: stop the server with Ctrl+C,
run `start_team.ps1` again, and share its new link. Internet can be available
on the network, but is not required to run the booking app. If Windows asks about
network access, allow the Python server on **Private networks** only. If the
site cannot be reached on college Wi-Fi, try a shared phone hotspot: some
networks prevent devices from connecting directly to one another. No router
port forwarding is needed.

## Separate accounts and testing

Each teammate opens **Sign up** and creates a personal passenger username and
password. Use a second, different username for an admin account if they want
separate passenger and admin roles. The leader signs in at `/admin/` with the
existing superuser, opens **Users**, selects the teammate's admin username,
checks **Staff status** and **Superuser status**, and saves. Only promote your
two trusted teammates: superusers can change all project data and users. Each
person signs in with their own password; nobody needs the leader's password.

Suggested division for testing:

1. Leader: create bus, seats and future trip in `/admin/`; show SQL Developer
   constraints, views, and query plans.
2. Teammate 1: sign up as passenger, reserve seats, confirm a simulated
   payment, inspect the ticket, then cancel it.
3. Teammate 2: sign up as another passenger, fill the last seats or join the
   waiting list, then inspect and accept a released-seat offer.

All accounts use the same Oracle data, so their actions will affect the same
seat map and reports. Run tests on a future trip. The app's payments are
simulated and do not charge anyone.

## GitHub without extra setup for teammates

The leader can continue making and pushing the project commits. Share the
repository URL so teammates can read the source and project documentation.
If the repository is private, invite their GitHub usernames through the
repository's **Settings → Collaborators** page. A GitHub login does not log
someone into the bus booking app; these are separate accounts.

The leader's simple checkpoint routine in a second PowerShell window is:

```powershell
git status --short
git add README.md docs/team_access.md
git commit -m "Document team access"
git push
```

Replace the filenames and commit message for later changes. Review
`git status --short` before staging; never add `.env`, passwords, database
dumps, or `.venv`. If teammates later want to edit code, give each a separate
Git clone and coordinate changes before pushing to `main`.
