# Family Access — requirements

Product: carelink patient portal · Author: product team · 2026-10-20

## Background
Patients increasingly manage care for parents, children and partners. Today they share passwords, which
we can't see or control. Family Access lets a patient give another person — a **caregiver** — access to
their record.

## Users
- **Patients** (≈ 400,000), web and mobile.
- **Caregivers**: any carelink account holder a patient invites.
- **Support staff** (≈ 40, outsourced contact centre): help patients and caregivers on the phone.
- **Clinicians** use the clinical system, not the portal; out of scope.
- **Lab vendor** (Northlab): runs the clinic network's lab tests.
- **Analytics team**: reports to clinic management.

## Requirements

1. **Caregiver access.** A patient invites a caregiver by e-mail; once accepted, the caregiver sees the
   patient's appointments, lab results and prescriptions, and can book appointments. Access lasts until
   the patient removes it. For children under 16 the parent is added automatically from the clinic's
   registration data. A caregiver can themselves invite further caregivers "so families can organise
   themselves".
2. **Support impersonation.** Support staff must be able to "see exactly what the patient sees" to help
   on calls. They log in as the patient from the support tool. Patients should not be bothered with
   notifications about it.
3. **Lab results.** Northlab pushes results to `POST /integrations/northlab/results` as JSON. Northlab
   suggested a fixed API key in a header; they can also sign requests if we ask.
4. **Analytics export.** Analytics wants a nightly export of appointments and lab results "anonymised"
   by removing names and e-mail addresses (keeping date of birth, postcode, clinic and test codes) to a
   shared bucket used by an external BI contractor.
5. **National ID.** We need the national health identifier (10 digits, the last one a check digit) to
   match records with the clinical system. To protect privacy we will **store it hashed with SHA-256**
   rather than in plain text.
6. **Account recovery.** Recovery should be simple: a code by **SMS to the phone number on file is the
   only recovery method**. Support can update the phone number on file after a call.
7. **Audit.** Clinic compliance must be able to answer "who saw this record, when" for any patient.

## Non-functional
- Availability 99.9 %; results must appear within 15 minutes of Northlab sending them.
- Hosted in the clinic network's existing cloud account; the portal runs as containers behind a load
  balancer, Postgres for data.
- Regulation: health data under national law and GDPR.

## Open from product
- Should caregivers see mental-health appointments?
- How long do we keep the export in the shared bucket?
