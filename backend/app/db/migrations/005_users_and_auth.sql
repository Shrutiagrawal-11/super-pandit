-- 001_init_schema.sql's `users` only had email NOT NULL, no password/phone
-- support. Extending it here rather than recreating: password_hash is
-- nullable because Google/Apple/phone-OTP users never set one; auth_identities
-- holds one row per sign-in method a user has linked (email, google,
-- apple, phone), so a user can have more than one without a redesign.

ALTER TABLE users
    ALTER COLUMN email DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS phone TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS password_hash TEXT,
    ADD COLUMN IF NOT EXISTS display_name TEXT,
    ADD CONSTRAINT users_email_or_phone CHECK (email IS NOT NULL OR phone IS NOT NULL);

CREATE TABLE IF NOT EXISTS auth_identities (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('email', 'google', 'apple', 'phone')),
    provider_uid TEXT NOT NULL,  -- email address, google sub, apple sub, or phone number
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_uid)
);

CREATE TABLE IF NOT EXISTS saved_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    verse_id BIGINT REFERENCES verses(id) ON DELETE CASCADE,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, verse_id)
);

CREATE TABLE IF NOT EXISTS reading_progress (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scripture TEXT NOT NULL,
    chapter INT NOT NULL,
    verse_number INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, scripture)
);
