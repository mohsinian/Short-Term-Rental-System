-- Migration: 003_add_property_constraints
-- Description: Enforce uniqueness on property_id and prepare for upserts

-- Add Unique Constraint for properties table
ALTER TABLE properties
ADD CONSTRAINT uq_properties_property_id UNIQUE (property_id);

-- Add Unique Constraint for Performance Table
ALTER TABLE property_performance
ADD CONSTRAINT uq_performance_property_id UNIQUE (property_id);