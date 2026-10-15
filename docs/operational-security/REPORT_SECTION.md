# Operational Security

## 1. Objective

The objective of this work was to improve the operational security of Tatou by adding security monitoring, reducing unnecessary network exposure, and collecting evidence that can support the investigation of suspicious activity.

## 2. Threat Modelling

The threat model identifies risks involving repeated login failures, unauthorized document access or deletion, database exposure, command injection, and insufficient logging. These risks could affect the confidentiality, integrity, or availability of the application and its data.

The threat model also identifies the need to preserve logs, investigate suspicious activity, fix vulnerabilities, and verify security fixes.

## 3. Implemented Security Improvements

### Login monitoring

The application records failed login attempts in its logs. It also generates a warning when three failed attempts for the same email address occur within five minutes. This provides an observation point for identifying repeated authentication failures.

The implemented behavior was tested using controlled invalid login requests. The logs recorded the failed attempts and the repeated-login warning. This demonstrates that the monitoring behavior worked during the test; it does not establish that an external attacker caused those attempts.

### Reduced database port exposure

The Docker Compose configuration was changed to remove the published database port. This reduces direct access to the database through a host-published port. It does not replace the need for database authentication, network controls, and secure configuration.

## 4. Incident Response

During the project, the team was notified that FLAG_2 had been captured by another group. The team investigated application functionality, including API handling, file handling, plugin loading, and watermarking. A command-injection weakness in the `bash-bridge-eof` watermarking method was identified and fixed.

The team rebuilt and redeployed the server, rotated FLAG_2, and verified the patched server. However, the investigation did not establish conclusively that this vulnerability was the exact path used to capture the flag.

## 5. Evidence and Verification

The repository contains evidence files documenting failed-login logging and repeated-login detection. These logs provide examples of the monitoring behavior during testing.

Code compilation, Git whitespace checks, and Docker Compose configuration validation were also used during verification. These checks help identify implementation or configuration problems, but they do not prove that every possible attack has been prevented.

## 6. Limitations and Further Work

The repeated-login mechanism generates warnings but does not automatically block further attempts. Its counter is held in application memory and may reset when the application restarts. Future improvements could include persistent security-event storage, alerting, monitoring for suspicious document operations, and additional recovery testing.

Operational security requires ongoing monitoring and investigation rather than relying on a single control.
