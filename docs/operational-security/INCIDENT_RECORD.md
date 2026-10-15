# Incident Record: FLAG_2 Capture

## 1. Incident Summary

On 21 September 2026, the team was notified that FLAG_2 had been captured by another group. The team investigated the Tatou application, addressed an identified security weakness, rotated the compromised flag, and verified the updated deployment.

The investigation did not establish conclusively that the identified vulnerability was the exact attack path used to capture the flag.

## 2. Investigation

The investigation examined API endpoints, authentication, document upload and retrieval, plugin loading, watermarking functionality, and the handling of sensitive configuration.

A significant command-injection vulnerability was identified in the `bash-bridge-eof` watermarking method. The original implementation used shell execution and incorporated input into shell commands, creating a risk of unintended command execution.

The team also examined plugin loading and document handling as potential security concerns. These investigations helped identify areas requiring attention, but the command-injection weakness was the main vulnerability addressed during this incident.

## 3. Containment and Remediation

The team took the following actions:

- Removed the unsafe shell-execution approach from the vulnerable watermarking method.
- Changed the implementation to process PDF data directly in Python.
- Rebuilt and redeployed the server with the security fix.
- Rotated FLAG_2 to the newly assigned value.
- Recreated the server container so it received the updated environment configuration.
- Verified that the server was running after redeployment.

Sensitive flag values were not included in the incident journal or this record.

## 4. Testing and Verification

The incident journal records the following verification results after the security change:

- All six tests in the watermarking test suite passed.
- The API tests passed.
- The running Docker container was checked to verify that the patched implementation was deployed.
- The server container was confirmed to be running after the security fix and flag rotation.

These results support the reported remediation and deployment checks. They do not prove that every possible attack path has been eliminated.

## 5. Evidence and Limitations

The supporting incident journal, `Journal.pdf`, documents the investigation, remediation, testing, flag rotation, and deployment verification.

The journal identifies a confirmed command-injection weakness. However, the team did not establish definitive evidence that this vulnerability was the exact mechanism used by the other group to capture FLAG_2. The incident record therefore distinguishes the confirmed vulnerability from the unconfirmed attack path.

Supporting evidence also includes the repository's login-monitoring test logs:

- `evidence/failed-login-evidence.txt`
- `evidence/repeated-login-evidence.txt`

These files demonstrate failed-login logging and repeated-login detection during controlled testing. They are separate from the investigation into the FLAG_2 capture.

## 6. Follow-up Actions and Lessons Learned

- Avoid shell execution when the operation can be performed safely using application code.
- Do not place untrusted input directly into shell commands.
- Verify security fixes in the running deployment, not only in source code.
- Rotate compromised secrets and verify that the running service receives the updated configuration.
- Preserve relevant logs and investigation notes for future incidents.
- Continue monitoring application logs and testing security controls.
- Record confirmed findings separately from assumptions about an attack path.
