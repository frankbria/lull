-- Isolated databases so tests never touch dev data.
-- lull_test     : model + entitlement tests (schema via create_all)
-- lull_migtest  : alembic upgrade/downgrade roundtrip (kept separate so it can drop everything)
CREATE DATABASE lull_test;
CREATE DATABASE lull_migtest;
