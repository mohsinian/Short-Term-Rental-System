-- Migration: 002_add_market_uniqueness
-- Description: Adds unique constraint on markets table for (name, state_name) combination

-- This constraint allows NULL state_name values to be unique among themselves
CREATE UNIQUE INDEX IF NOT EXISTS idx_markets_name_state_unique
ON markets (name, state_name);
