# Security Policy — AgriTech Technological Foods

## Credential Management

### Never commit secrets to the repository

All credentials, API keys, passwords, and tokens must be kept out of version control.
This project uses `.gitignore` rules and `.example` template files to enforce this.

### How credentials work in this project

| Component | Secret file (gitignored) | Template file (committed) |
|-----------|-------------------------|--------------------------|
| Backend API | `backend/.env` | `backend/.env.example` |
| Arduino (temp_hum_light) | `arduino/temp_hum_light_sending_api/config.h` | `arduino/temp_hum_light_sending_api/config.h.example` |
| Arduino (prod) | `arduino/.../temp_hum_light_sending_api_prod/config.h` | `arduino/.../temp_hum_light_sending_api_prod/config.h.example` |
| Arduino (dual sensor) | `arduino/dual_sensor_system/config.h` | `arduino/dual_sensor_system/config.h.example` |
| SonarQube | `sonarqube/.env` | `sonarqube/.env.example` |
| Infrastructure | `infra/.env` | `infra/.env.example` |

### Setting up credentials

1. Copy the `.example` file to its secret counterpart (e.g., `cp config.h.example config.h`)
2. Fill in your real values
3. **Never** commit the secret file — `.gitignore` blocks it, but verify with `git status` before committing

### What to do if credentials are leaked

If any secret is accidentally committed or exposed:

1. **Rotate immediately** — change the credential at its source (WiFi router, API provider, database, etc.)
2. **Revoke the old credential** — don't just change it, ensure the old one no longer works
3. **Remove from git history** — use `git filter-branch` or [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) to purge the secret from all commits
4. **Audit access** — check logs for unauthorized use of the leaked credential
5. **Update `.gitignore`** — ensure the file pattern is excluded to prevent future leaks

### Credentials that were rotated (2026-02-10)

The following credentials were found in plaintext in the repository and should be considered **compromised**. They have been removed from version control but must be **rotated at their source**:

- WiFi SSID/password (previously in `config.h` files)
- API keys (backend `API_KEY`, any Anthropic API key)
- Server/Raspberry Pi passwords
- KeePassXC database master password (if reused)

**Action required by the project maintainer:**

- [ ] Change WiFi password on the router
- [ ] Regenerate the backend API key in `backend/.env`
- [ ] Change Raspberry Pi SSH password
- [ ] Rotate any Anthropic API key that was exposed
- [ ] Verify KeePassXC master password is unique and not reused
- [ ] Consider running BFG Repo-Cleaner to remove secrets from git history

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately
by opening a GitHub issue with the `security` label or contacting the maintainer directly.
Do not disclose vulnerabilities publicly until they have been addressed.

# Security Policy — AgriTech Technological Foods

## Credential Management

### Never commit secrets to the repository

All credentials, API keys, passwords, and tokens must be kept out of version control.
This project uses `.gitignore` rules and `.example` template files to enforce this.

### How credentials work in this project

| Component | Secret file (gitignored) | Template file (committed) |
|-----------|-------------------------|--------------------------|
| Backend API | `backend/.env` | `backend/.env.example` |
| Arduino (temp_hum_light) | `arduino/temp_hum_light_sending_api/config.h` | `arduino/temp_hum_light_sending_api/config.h.example` |
| Arduino (prod) | `arduino/temp_hum_light_sending_api/temp_hum_light_sending_api_prod/config.h` | `arduino/temp_hum_light_sending_api/temp_hum_light_sending_api_prod/config.h.example` |
| Arduino (dual sensor) | `arduino/dual_sensor_system/config.h` | `arduino/dual_sensor_system/config.h.example` |
| SonarQube | `sonarqube/.env` | `sonarqube/.env.example` |
| Infrastructure | `infra/.env` | `infra/.env.example` |

### Setting up credentials

1. Copy the `.example` file to its secret counterpart (e.g., `cp config.h.example config.h`)
2. Fill in your real values
3. **Never** commit the secret file — `.gitignore` blocks it, but verify with `git status` before committing

### What to do if credentials are leaked

If any secret is accidentally committed or exposed:

1. **Rotate immediately** — change the credential at its source (WiFi router, API provider, database, etc.)
2. **Revoke the old credential** — don't just change it, ensure the old one no longer works
3. **Remove from git history** — use `git filter-branch` or [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) to purge the secret from all commits
4. **Audit access** — check logs for unauthorized use of the leaked credential
5. **Update `.gitignore`** — ensure the file pattern is excluded to prevent future leaks

### Credentials that were rotated (2026-02-10)

The following credentials were found in plaintext in the repository and should be considered **compromised**. They have been removed from version control but must be **rotated at their source**:

- WiFi SSID/password (in `config.h` files)
- API keys (backend `API_KEY`, any Anthropic API key)
- Server/Raspberry Pi passwords
- KeePassXC database master password (if reused)

**Action required by the project maintainer:**
- [ ] Change WiFi password on the router
- [ ] Regenerate the backend API key in `backend/.env`
- [ ] Change Raspberry Pi SSH password
- [ ] Rotate any Anthropic API key that was exposed
- [ ] Verify KeePassXC master password is unique and not reused

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately by opening a GitHub issue with the `security` label or contacting the maintainer directly. Do not disclose vulnerabilities publicly until they have been addressed.
