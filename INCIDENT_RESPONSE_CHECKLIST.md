# Security Incident Response Checklist

This checklist is based on lessons learned from security incidents during the Tatou project. Its purpose is to provide a consistent process for responding to future security incidents.

## 1. Record the incident

- Record the date and a short description of the incident.
- Record how the incident was discovered or reported.
- Identify the affected part of the system.

## 2. Investigate

- Collect relevant evidence before making changes where possible.
- Investigate possible causes and affected components.
- Separate confirmed evidence from assumptions.
- Do not claim an attack method as the cause unless there is evidence supporting it.

## 3. Contain the incident

- Limit the identified exposure where possible.
- If a secret or flag is compromised, rotate it to the newly assigned value.
- Make sure the compromised value is no longer used by the running system.

## 4. Apply a security fix

- Fix identified security weaknesses where possible.
- Avoid making unrelated changes during the incident response.
- Record what was changed and why.

## 5. Test and deploy

- Test the security change.
- Check that existing functionality still works.
- Rebuild or recreate affected services when necessary.
- Verify that the running deployment contains the intended fix.

## 6. Document the result

- Record the actions taken and the final status.
- Record any remaining limitations or uncertainties.
- Document lessons learned and possible follow-up security improvements.
