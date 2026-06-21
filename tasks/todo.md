# Issue #5 / #32 — Python-native auth slice

Closes the remaining scope of #5 (data layer shipped in #31). Implements #32.

## Decisions (need sign-off)
- **JWT/crypto lib: `pyjwt[crypto]` instead of Authlib.** Native mobile sign-in sends a
  provider `id_token`; the backend only *verifies* it (RS256 against provider JWKS) and issues
  our own session JWT (HS256). PyJWT covers both with one dep; Authlib's auth-code/redirect
  machinery would be unused. `passlib[argon2]` for password hashing (as specified).
- **OAuth shape: token-verification, not redirect flow.** `POST /auth/oauth/{provider}` takes
  `{id_token, age_confirmed}`, verifies signature + audience + exp against Google/Apple JWKS,
  extracts the verified email, upserts the user. Matches how Expo/RN native sign-in works.
- **Account linking by verified email.** OAuth + email/pw with same (provider-verified) email →
  same account. No schema change needed for OAuth (`password_hash` stays null for oauth-only).
- **Generation gating wired into `/tts`** (the billable render), not `/script` (free text preview).
- **Guest mode** enforced server-side via a client-supplied `X-Guest-Id` UUID + a small
  `guest_credits` table (mirrors `GenerationCredit`): 1 free `/tts`, then 401 → prompt signup.

## Plan (TDD: RED → GREEN → REFACTOR per slice)

1. **Deps + settings** — add `pyjwt[crypto]`, `passlib[argon2]` to pyproject; add
   `jwt_secret`, `jwt_expire_minutes`, `google_client_ids`, `apple_client_ids` to config;
   document in `.env.example`.
2. **security.py** — argon2 `hash_password`/`verify_password`; `create_access_token(user_id)` /
   `decode_access_token` (HS256, exp).
3. **GuestCredit model + migration** — `guest_credits {id, guest_id unique, used}`; Alembic
   revision down_revision=1551d5331491. Migration round-trip test.
4. **oauth.py** — `OAuthVerifier` seam (`get_oauth_verifier` dependency, like `get_source`):
   prod impl verifies id_token via `PyJWKClient` per provider; returns verified email. Tests
   override the dependency with a verifier backed by a real test RSA keypair (real RS256 verify,
   test issuer key — no mocking of our code).
5. **auth.py router** — `POST /auth/signup` (argon2, 18+ age gate → 422, dup → 409),
   `POST /auth/login` (401 on bad creds), `POST /auth/oauth/{provider}`, `GET /auth/me`;
   `current_user` (HTTPBearer→JWT→User) and `current_user_optional` deps.
6. **Wire entitlements into `/tts`** — authed: `has_access` + `record_generation`; guest
   (no token, `X-Guest-Id`): 1 free then 401. Include router in main.py.
7. **Quality gate** — ruff + black + full pytest (real Postgres); cross-family review;
   demo every AC with outcome evidence; CI; docs sync; PR → merge; close #5 + #32.

## Acceptance criteria (from #32)
- [ ] Email/password signup + login (argon2 → `User.password_hash`)
- [ ] OAuth (Google + Apple) id_token verification
- [ ] 18+ age gate enforced at account creation (sets `User.age_verified`)
- [ ] JWT issuance + `current_user` FastAPI dependency
- [ ] Guest mode: one free generation before account creation (FR-A2)
- [ ] `record_generation()` / `has_access()` wired into the authed generation path

## Notes
- Onboarding/consent flow (FR-O1..O4) is explicitly out of scope (Sprint-3 gate).
- Test DB: `docker compose -f apps/api/docker-compose.yml up -d` (lull_test database).
