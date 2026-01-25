-- Migration: 001_initial_schema
-- Description: Creates basic tables for STR Market Data

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Schema Version Control Table
-- This table tracks which migrations have been successfully executed.
CREATE TABLE IF NOT EXISTS schema_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    success BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Core Entity: Markets
-- Normalized lookup table for geographic markets.
CREATE TABLE IF NOT EXISTS markets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    state_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Core Entity: Hosts
-- Normalized lookup table for property managers/hosts.
CREATE TABLE IF NOT EXISTS hosts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    airbnb_host_id VARCHAR(255) UNIQUE, -- The ID found in Airbnb URL
    airbnb_host_url TEXT,
    is_super_host BOOLEAN DEFAULT NULL, -- Can be updated dynamically
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Core Entity: Properties
-- Stores structural, static data about the property.
CREATE TABLE IF NOT EXISTS properties (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,

    -- Foreign Keys
    market_id UUID REFERENCES markets(id) ON DELETE SET NULL,
    host_id UUID REFERENCES hosts(id) ON DELETE SET NULL,

    -- Identifiers
    property_id VARCHAR(255) NOT NULL, -- The clean ID from your CSV (e.g. 'abnb_...')
    airbnb_listing_url TEXT,
    vrbo_listing_url TEXT,

    -- Naming & Descriptions
    title VARCHAR(500),
    listing_name VARCHAR(500),
    description TEXT, -- Stripped HTML

    -- Location
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    zipcode VARCHAR(20),
    city_name VARCHAR(100),

    -- Physical Attributes
    bedrooms NUMERIC, -- Allows for non-integer if needed (though rare)
    bathrooms NUMERIC,
    accommodates INTEGER,
    property_type VARCHAR(100), -- e.g. 'Entire home/apt'
    room_type VARCHAR(100),    -- e.g. 'Entire home/apt'
    beds INTEGER,

    -- Policy & Pricing Tier
    price_tier INTEGER, -- 1-5 scale
    instant_book BOOLEAN,
    min_stay INTEGER,

    -- Flags
    is_guest_favorite BOOLEAN DEFAULT FALSE,
    is_reliable_data BOOLEAN DEFAULT TRUE, -- Derived from Data Quality Category

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for Properties
CREATE INDEX IF NOT EXISTS idx_properties_market_id ON properties(market_id);
CREATE INDEX IF NOT EXISTS idx_properties_host_id ON properties(host_id);
CREATE INDEX IF NOT EXISTS idx_properties_property_id ON properties(property_id);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(latitude, longitude);

-- 6. Amenity Data: Denormalized (JSONB)
-- Stores the amenities as a JSONB blob for flexible querying.
-- Kept separate to avoid row bloat in the main properties table.
CREATE TABLE IF NOT EXISTS property_amenities (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    amenities JSONB NOT NULL, -- e.g. {"Pool": true, "Gym": true, "list": ["Wifi", "Kitchen"]}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure 1:1 relationship effectively
CREATE UNIQUE INDEX IF NOT EXISTS idx_property_amenities_property_id ON property_amenities(property_id);
-- GIN Index for efficient JSONB querying
CREATE INDEX IF NOT EXISTS idx_property_amenities_gin ON property_amenities USING GIN (amenities);

-- 7. Performance Metrics: Semi-Normalized
-- Stores financial and review data. 
-- Separated because this data changes frequently and is queried differently than static attributes.
CREATE TABLE IF NOT EXISTS property_performance (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Financials
    revenue NUMERIC,
    revenue_potential NUMERIC,
    adr NUMERIC, -- Average Daily Rate
    cleaning_fee NUMERIC,
    occupancy NUMERIC, -- Percentage (0.0 to 1.0 or 0-100)
    available_nights INTEGER,

    -- Reviews & Ratings
    total_reviews INTEGER,
    rating NUMERIC,
    property_reviews_count INTEGER, -- If different from total_reviews

    -- Data Quality Info
    high_season_reviews INTEGER,
    high_season_label VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_property_performance_property_id ON property_performance(property_id);
CREATE INDEX IF NOT EXISTS idx_property_performance_revenue ON property_performance(revenue DESC);