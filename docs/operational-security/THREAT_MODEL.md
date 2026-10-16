# Operational Security Threat Model

## 1. System Overview

Tatou is a document-sharing application. Its operational security depends on protecting user accounts, uploaded documents, application services, and the database.

## 2. Assets to Protect

- User accounts and login credentials
- Uploaded documents and their confidentiality
- Database records and stored application data
- Application availability and integrity
- Flags and other sensitive project information
- Logs needed for security monitoring and incident investigation

## 3. Potential Threats

| Threat | Potential Impact |
|---|---|
| Repeated failed login attempts | Attempts to guess or discover account credentials |
| Unauthorized document access | Exposure of confidential documents |
| Unauthorized document deletion | Loss of user documents |
| Database exposure | Unauthorized access to stored data |
| Command injection through watermarking functionality | Unauthorized command execution or compromise of the server |
| Insufficient logging | Delayed detection and investigation of attacks |

These are identified risks, not a claim that every threat occurred during the project.

## 4. Existing Controls and Observation Points

- Failed login attempts are recorded in application logs.
- Repeated failed logins for the same email are reported through a warning after three attempts within five minutes.
- Database port exposure through Docker Compose has been reduced.
- Application validation and access-control checks help protect document operations.
- Logs provide evidence for investigating failed authentication attempts.

## 5. Incident Detection and Response

When suspicious activity is detected, the team should preserve relevant logs, investigate the affected functionality, identify and fix the vulnerability where possible, test the fix, and redeploy the application when appropriate. Exposed flags or credentials should be rotated when necessary.

## 6. Limitations and Further Work

The repeated-login detection currently generates a warning; it does not automatically block an account or IP address. The counter is held in memory and may reset when the application restarts. Additional work could include persistent security logs, alerts, monitoring for unauthorized document operations, and testing of recovery procedures.
