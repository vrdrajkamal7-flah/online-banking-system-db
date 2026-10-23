ONLINE BANKING SYSTEM - ORACLE + FLASK + HTML
================================================

PROJECT STACK
-------------
Oracle Database + Python Flask + HTML/CSS/JavaScript.
The supplied banking UI is retained. Flask serves index.html and provides
Gmail OTP plus Oracle persistence APIs.

1. INSTALL SOFTWARE
--------------------
Install:
- Oracle Database XE (or another Oracle Database)
- Oracle SQL Developer
- Python 3.11 or newer

2. CREATE THE DATABASE TABLES
-----------------------------
Open Oracle SQL Developer.
Connect to your Oracle user, normally the XEPDB1/PDB user for XE.
Open oracle_schema.sql and press Run Script (F5).

The script creates:
- OB_BANKS
- OB_USERS
- OB_ACCOUNTS
- OB_TRANSACTIONS
- OB_KYC
- OB_STATE
- OB_EMPLOYEES
- OB_MANAGERS
- OB_CEO
- balance and transaction triggers
- OB_TRANSFER_MONEY stored procedure

3. OPEN THE PROJECT
-------------------
Open Command Prompt or PowerShell and run:

cd C:\Users\admin\VSCODE\online_banking_oracle

If you copied the project somewhere else, use that folder instead.

4. CREATE PYTHON VIRTUAL ENVIRONMENT
------------------------------------
Windows:

py -m venv .venv
.venv\Scripts\activate

Then:

python -m pip install -r requirements.txt

If PowerShell blocks activation, you can use Command Prompt instead:

.venv\Scripts\activate.bat

5. SET ORACLE CONNECTION DETAILS
--------------------------------
For Oracle XE with the default XEPDB1 service, examples are:

set ORACLE_USER=YOUR_ORACLE_USERNAME
set ORACLE_PASSWORD=YOUR_ORACLE_PASSWORD
set ORACLE_DSN=localhost:1521/XEPDB1

PowerShell version:

$env:ORACLE_USER="YOUR_ORACLE_USERNAME"
$env:ORACLE_PASSWORD="YOUR_ORACLE_PASSWORD"
$env:ORACLE_DSN="localhost:1521/XEPDB1"

Replace YOUR_ORACLE_USERNAME and YOUR_ORACLE_PASSWORD with the Oracle
account that ran oracle_schema.sql.

6. OPTIONAL: GMAIL OTP
----------------------
For Gmail OTP, set:

$env:SMTP_EMAIL="yourgmail@gmail.com"
$env:SMTP_PASSWORD="YOUR_GMAIL_APP_PASSWORD"

SMTP_PASSWORD must be a Gmail App Password, not the normal Gmail password.

7. START THE WEBSITE
--------------------
Run:

python backend_app.py

You should see Flask listening on port 5000.

Open Chrome:

http://127.0.0.1:5000/

8. TEST ORACLE CONNECTION
-------------------------
Open:

http://127.0.0.1:5000/api/db-test

Expected result contains:

"database": "Oracle"
"connected": true

9. TEST THE APPLICATION
-----------------------
Register a customer using the Gmail OTP flow.
Login with the email and password.
Complete the KYC flow.
Use the employee login for the selected bank.
Approve the KYC.
Login again and create/use the account.
Test account details, balance, transfer and transaction history.

10. STAFF LOGIN CREDENTIALS
---------------------------
CEO:
username: CEO
password: CEO of OBS

Indian Bank employee:
username: EMPIND
password: INDIAN BANK OBS

SBI employee:
username: EMPSBI
password: SBI OBS

Axis employee:
username: EMPAXIS
password: AXIS BANK OBS

HDFC employee:
username: EMPHDFC
password: HDFC BANK OBS

IDFC employee:
username: EMPIDFC
password: IDFC FIRST BANK OBS

ICICI employee:
username: EMPICICI
password: ICICI BANK OBS

Managers are also seeded in Oracle using the BANKMAN pattern, for example:
INDIANMAN, SBIMAN, AXISMAN, HDFCMAN, IDFCMAN, ICICIMAN.

NOTE: The supplied HTML currently contains its original employee/CEO login
logic. The Oracle manager table is ready for the next manager-login wiring.

11. IMPORTANT ARCHITECTURE NOTE
--------------------------------
The existing frontend was written around a JavaScript state object. This
version loads that persistent state from Oracle at startup and saves changes
to Oracle through /api/state. The backend also rebuilds the normalized Oracle
tables for DBMS-project demonstration and includes an Oracle transfer
procedure, triggers, constraints, and COMMIT/ROLLBACK logic.

For a production banking application, passwords and PINs should be hashed
and transfer authorization should be performed entirely server-side. This
student project keeps the original frontend behavior so the existing UI and
workflow remain intact.
