-- Migration: Add country and profession fields to users table
-- Date: 2025-10-25

ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS profession VARCHAR(255);
