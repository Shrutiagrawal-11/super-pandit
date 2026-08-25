-- 001_init_schema.sql left ritual_sessions.user_id without a FK, noting
-- "added once users table has real auth (Phase 2)" -- that's now true.
ALTER TABLE ritual_sessions
    ALTER COLUMN user_id SET NOT NULL,
    ADD CONSTRAINT ritual_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
