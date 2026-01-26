-- Migration: 004_add_temp_tables
-- Description: Add upsert helper functions for efficient bulk operations
--
-- This migration adds helper functions for upsert operations.
-- Temp tables are created dynamically in the batch loader to ensure
-- they exist in the same session as the COPY operations.
--
-- Note: Temp tables in PostgreSQL are session-specific. They only exist
-- for the duration of the database connection that created them.
-- Since the batch loader runs in a separate connection from migrations,
-- temp tables are created dynamically in the batch loader methods themselves.

-- ============================================================================
-- HELPER FUNCTIONS FOR UPSERT FROM TEMP TABLES
-- ============================================================================

-- Function to upsert hosts from temp table
CREATE OR REPLACE FUNCTION upsert_hosts_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing hosts
    UPDATE hosts h
    SET 
        airbnb_host_url = COALESCE(t.airbnb_host_url, h.airbnb_host_url),
        is_super_host = COALESCE(t.is_super_host, h.is_super_host),
        updated_at = NOW()
    FROM hosts_temp t
    WHERE h.airbnb_host_id = t.airbnb_host_id
    AND (
        h.airbnb_host_url IS DISTINCT FROM t.airbnb_host_url
        OR h.is_super_host IS DISTINCT FROM t.is_super_host
    );
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    
    -- Insert new hosts
    INSERT INTO hosts (id, airbnb_host_id, airbnb_host_url, is_super_host, created_at, updated_at)
    SELECT 
        t.id,
        t.airbnb_host_id,
        t.airbnb_host_url,
        t.is_super_host,
        t.created_at,
        t.updated_at
    FROM hosts_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM hosts h WHERE h.airbnb_host_id = t.airbnb_host_id
    );
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    -- Clear temp table
    TRUNCATE TABLE hosts_temp;
    
    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

-- Function to upsert properties from temp table
CREATE OR REPLACE FUNCTION upsert_properties_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing properties
    UPDATE properties p
    SET 
        market_id = COALESCE(t.market_id, p.market_id),
        host_id = COALESCE(t.host_id, p.host_id),
        airbnb_listing_url = COALESCE(t.airbnb_listing_url, p.airbnb_listing_url),
        vrbo_listing_url = COALESCE(t.vrbo_listing_url, p.vrbo_listing_url),
        title = COALESCE(t.title, p.title),
        listing_name = COALESCE(t.listing_name, p.listing_name),
        description = COALESCE(t.description, p.description),
        latitude = COALESCE(t.latitude, p.latitude),
        longitude = COALESCE(t.longitude, p.longitude),
        zipcode = COALESCE(t.zipcode, p.zipcode),
        city_name = COALESCE(t.city_name, p.city_name),
        bedrooms = COALESCE(t.bedrooms, p.bedrooms),
        bathrooms = COALESCE(t.bathrooms, p.bathrooms),
        accommodates = COALESCE(t.accommodates, p.accommodates),
        property_type = COALESCE(t.property_type, p.property_type),
        room_type = COALESCE(t.room_type, p.room_type),
        beds = COALESCE(t.beds, p.beds),
        price_tier = COALESCE(t.price_tier, p.price_tier),
        instant_book = COALESCE(t.instant_book, p.instant_book),
        min_stay = COALESCE(t.min_stay, p.min_stay),
        is_guest_favorite = COALESCE(t.is_guest_favorite, p.is_guest_favorite),
        is_reliable_data = COALESCE(t.is_reliable_data, p.is_reliable_data),
        updated_at = NOW()
    FROM properties_temp t
    WHERE p.property_id = t.property_id
    AND (
        p.market_id IS DISTINCT FROM t.market_id
        OR p.host_id IS DISTINCT FROM t.host_id
        OR p.airbnb_listing_url IS DISTINCT FROM t.airbnb_listing_url
        OR p.vrbo_listing_url IS DISTINCT FROM t.vrbo_listing_url
        OR p.title IS DISTINCT FROM t.title
        OR p.listing_name IS DISTINCT FROM t.listing_name
        OR p.description IS DISTINCT FROM t.description
        OR p.latitude IS DISTINCT FROM t.latitude
        OR p.longitude IS DISTINCT FROM t.longitude
        OR p.zipcode IS DISTINCT FROM t.zipcode
        OR p.city_name IS DISTINCT FROM t.city_name
        OR p.bedrooms IS DISTINCT FROM t.bedrooms
        OR p.bathrooms IS DISTINCT FROM t.bathrooms
        OR p.accommodates IS DISTINCT FROM t.accommodates
        OR p.property_type IS DISTINCT FROM t.property_type
        OR p.room_type IS DISTINCT FROM t.room_type
        OR p.beds IS DISTINCT FROM t.beds
        OR p.price_tier IS DISTINCT FROM t.price_tier
        OR p.instant_book IS DISTINCT FROM t.instant_book
        OR p.min_stay IS DISTINCT FROM t.min_stay
        OR p.is_guest_favorite IS DISTINCT FROM t.is_guest_favorite
        OR p.is_reliable_data IS DISTINCT FROM t.is_reliable_data
    );
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    
    -- Insert new properties
    INSERT INTO properties (
        id, market_id, host_id, property_id, airbnb_listing_url, vrbo_listing_url,
        title, listing_name, description, latitude, longitude, zipcode, city_name,
        bedrooms, bathrooms, accommodates, property_type, room_type, beds,
        price_tier, instant_book, min_stay, is_guest_favorite, is_reliable_data,
        created_at, updated_at
    )
    SELECT 
        t.id, t.market_id, t.host_id, t.property_id, t.airbnb_listing_url, t.vrbo_listing_url,
        t.title, t.listing_name, t.description, t.latitude, t.longitude, t.zipcode, t.city_name,
        t.bedrooms, t.bathrooms, t.accommodates, t.property_type, t.room_type, t.beds,
        t.price_tier, t.instant_book, t.min_stay, t.is_guest_favorite, t.is_reliable_data,
        t.created_at, t.updated_at
    FROM properties_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM properties p WHERE p.property_id = t.property_id
    );
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    -- Clear temp table
    TRUNCATE TABLE properties_temp;
    
    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

-- Function to upsert property_performance from temp table
CREATE OR REPLACE FUNCTION upsert_property_performance_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing performance records
    UPDATE property_performance p
    SET 
        revenue = COALESCE(t.revenue, p.revenue),
        revenue_potential = COALESCE(t.revenue_potential, p.revenue_potential),
        adr = COALESCE(t.adr, p.adr),
        cleaning_fee = COALESCE(t.cleaning_fee, p.cleaning_fee),
        occupancy = COALESCE(t.occupancy, p.occupancy),
        available_nights = COALESCE(t.available_nights, p.available_nights),
        total_reviews = COALESCE(t.total_reviews, p.total_reviews),
        rating = COALESCE(t.rating, p.rating),
        property_reviews_count = COALESCE(t.property_reviews_count, p.property_reviews_count),
        high_season_reviews = COALESCE(t.high_season_reviews, p.high_season_reviews),
        high_season_label = COALESCE(t.high_season_label, p.high_season_label),
        updated_at = NOW()
    FROM property_performance_temp t
    WHERE p.property_id = t.property_id
    AND (
        p.revenue IS DISTINCT FROM t.revenue
        OR p.revenue_potential IS DISTINCT FROM t.revenue_potential
        OR p.adr IS DISTINCT FROM t.adr
        OR p.cleaning_fee IS DISTINCT FROM t.cleaning_fee
        OR p.occupancy IS DISTINCT FROM t.occupancy
        OR p.available_nights IS DISTINCT FROM t.available_nights
        OR p.total_reviews IS DISTINCT FROM t.total_reviews
        OR p.rating IS DISTINCT FROM t.rating
        OR p.property_reviews_count IS DISTINCT FROM t.property_reviews_count
        OR p.high_season_reviews IS DISTINCT FROM t.high_season_reviews
        OR p.high_season_label IS DISTINCT FROM t.high_season_label
    );
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    
    -- Insert new performance records
    INSERT INTO property_performance (
        id, property_id, revenue, revenue_potential, adr, cleaning_fee,
        occupancy, available_nights, total_reviews, rating,
        property_reviews_count, high_season_reviews, high_season_label,
        created_at, updated_at
    )
    SELECT 
        t.id, t.property_id, t.revenue, t.revenue_potential, t.adr, t.cleaning_fee,
        t.occupancy, t.available_nights, t.total_reviews, t.rating,
        t.property_reviews_count, t.high_season_reviews, t.high_season_label,
        t.created_at, t.updated_at
    FROM property_performance_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM property_performance p WHERE p.property_id = t.property_id
    );
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    -- Clear temp table
    TRUNCATE TABLE property_performance_temp;
    
    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

-- Function to upsert property_amenities from temp table
CREATE OR REPLACE FUNCTION upsert_property_amenities_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing amenities (REPLACE entire JSON blob, not merge)
    UPDATE property_amenities p
    SET 
        amenities = t.amenities,
        updated_at = NOW()
    FROM property_amenities_temp t
    WHERE p.property_id = t.property_id
    AND p.amenities IS DISTINCT FROM t.amenities;
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    
    -- Insert new amenities
    INSERT INTO property_amenities (id, property_id, amenities, created_at, updated_at)
    SELECT 
        t.id, t.property_id, t.amenities, t.created_at, t.updated_at
    FROM property_amenities_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM property_amenities p WHERE p.property_id = t.property_id
    );
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    -- Clear temp table
    TRUNCATE TABLE property_amenities_temp;
    
    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON FUNCTION upsert_hosts_from_temp() IS 'Upsert hosts from hosts_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';
COMMENT ON FUNCTION upsert_properties_from_temp() IS 'Upsert properties from properties_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';
COMMENT ON FUNCTION upsert_property_performance_from_temp() IS 'Upsert property_performance from property_performance_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';
COMMENT ON FUNCTION upsert_property_amenities_from_temp() IS 'Upsert property_amenities from property_amenities_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts. Note: Replaces entire amenities JSON blob (not merge) to prevent "zombie amenities".';
