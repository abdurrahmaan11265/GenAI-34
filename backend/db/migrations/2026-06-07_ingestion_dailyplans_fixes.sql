-- Migration: 2026-06-07 — ingestion fixes, daily plans, sub-topics
--
-- Idempotent delta for databases built from the EARLIER schema.sql. Fresh
-- databases get all of this from the corrected schema.sql directly; run this
-- only to upgrade an existing DB. Safe to run multiple times.
--
-- Covers:
--   1. upload_status enum was created with malformed (escaped-quote) labels,
--      which made book_uploads fail to create. Ensure the enum + table exist.
--   2. books.file_url must be nullable (2-step upload + delete-after-build).
--   3. New daily_plans table (persisted soft-focus daily plan).
--   4. Sub-topics live in concepts.metadata->'subtopics' (no DDL needed).

BEGIN;

-- 1. upload_status enum + book_uploads -------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_status') THEN
        CREATE TYPE upload_status AS ENUM ('PENDING', 'STORED', 'FAILED');
    END IF;
END$$;
-- Backfill labels if the enum was created empty/malformed by the old schema.
ALTER TYPE upload_status ADD VALUE IF NOT EXISTS 'PENDING';
ALTER TYPE upload_status ADD VALUE IF NOT EXISTS 'STORED';
ALTER TYPE upload_status ADD VALUE IF NOT EXISTS 'FAILED';

CREATE TABLE IF NOT EXISTS book_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    mime_type TEXT,
    upload_status upload_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_book_uploads_book ON book_uploads(book_id);
CREATE INDEX IF NOT EXISTS idx_book_uploads_user ON book_uploads(user_id);

ALTER TABLE source_chunks    ADD COLUMN IF NOT EXISTS book_upload_id UUID REFERENCES book_uploads(id) ON DELETE CASCADE;
ALTER TABLE graph_build_jobs ADD COLUMN IF NOT EXISTS book_upload_id UUID REFERENCES book_uploads(id) ON DELETE CASCADE;

-- 2. file_url nullable ------------------------------------------------------
ALTER TABLE books ALTER COLUMN file_url DROP NOT NULL;

-- 3. daily_plans ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    plan_date DATE NOT NULL,
    learn_concept_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_daily_plan UNIQUE (user_id, book_id, plan_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_plans_user_book ON daily_plans(user_id, book_id, plan_date DESC);

COMMIT;
