# Security policy

Do not put API keys, personal data, unredacted incident payloads, or raw agent traces in issues or pull requests. Store credentials in environment variables; `.env.example` must contain placeholders only. Raw experimental output belongs under `runs/`, excluded by `.gitignore`.

Use a private channel to report vulnerabilities. GitHub private vulnerability reporting is currently unavailable on this repository; do not assume the Security tab provides it. For sprint-related disclosure, use the organizer's support channel at sprints@apartresearch.com without including exploit details in the initial message.

Experiments must use fake records, an isolated local tool interpreter, no shell execution of model output, and no network access from workers. The host owns execution records and identity mapping. A hash chain alone does not establish completeness or prevent a compromised host rewriting history.

Release benign schemas, analysis, aggregate statistics and reproducible toy fixtures. Assess newly discovered operational attacks under Apart's responsible disclosure policy before releasing them: https://apartresearch.com/info/responsible-disclosure-policy .

GitHub returned HTTP 422 when enabling secret scanning and push protection for this private repository on 2026-11-06. These protections are not enabled. Branch protection is enabled; privacy has not been changed.
