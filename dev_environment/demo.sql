-- Demo SQL for FAIRagro SQL-to-ARC
-- This is a minimal dataset with 10 investigations for demonstration purposes.

CREATE TABLE IF NOT EXISTS "vInvestigation" (
    identifier TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description_text TEXT NOT NULL,
    submission_date TIMESTAMP,
    public_release_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "vContact" (
    last_name TEXT,
    first_name TEXT,
    mid_initials TEXT,
    email TEXT,
    phone TEXT,
    fax TEXT,
    postal_address TEXT,
    affiliation TEXT,
    roles TEXT,
    investigation_ref TEXT,
    target_type TEXT DEFAULT 'investigation',
    target_ref TEXT
);

CREATE TABLE IF NOT EXISTS "vStudy" (
    identifier TEXT PRIMARY KEY,
    title TEXT,
    description_text TEXT,
    submission_date TIMESTAMP,
    public_release_date TIMESTAMP,
    investigation_ref TEXT
);

CREATE TABLE IF NOT EXISTS "vAssay" (
    identifier TEXT PRIMARY KEY,
    measurement_type_term TEXT,
    technology_type_term TEXT,
    technology_platform TEXT,
    investigation_ref TEXT,
    study_ref TEXT,
    title TEXT,
    description_text TEXT,
    measurement_type_uri TEXT,
    measurement_type_version TEXT,
    technology_type_uri TEXT,
    technology_type_version TEXT
);

CREATE TABLE IF NOT EXISTS "vPublication" (
    investigation_ref TEXT,
    target_type TEXT DEFAULT 'investigation',
    pubmed_id TEXT,
    doi TEXT,
    authors TEXT,
    title TEXT,
    status_term TEXT,
    status_uri TEXT,
    status_version TEXT,
    target_ref TEXT
);

CREATE TABLE IF NOT EXISTS "vAnnotationTable" (
    table_name TEXT,
    target_type TEXT,
    target_ref TEXT,
    investigation_ref TEXT,
    column_type TEXT,
    column_io_type TEXT,
    column_value TEXT,
    column_annotation_term TEXT,
    column_annotation_uri TEXT,
    column_annotation_version TEXT,
    row_index INTEGER,
    cell_value TEXT,
    cell_annotation_term TEXT,
    cell_annotation_uri TEXT,
    cell_annotation_version TEXT
);

-- Insert 10 demo investigations
INSERT INTO "vInvestigation" (identifier, title, description_text, submission_date, public_release_date) VALUES
('INV001', 'Soil Microbiome Study A', 'Analysis of soil microbiome in temperate forests.', '2023-01-15', '2023-06-01'),
('INV002', 'Wheat Yield Optimization', 'Field trials for drought-resistant wheat varieties.', '2023-02-10', '2023-07-15'),
('INV003', 'Peatland Carbon Sequestration', 'Long-term monitoring of carbon flux in northern peatlands.', '2023-03-05', '2023-08-20'),
('INV004', 'Invasive Species Impact', 'Study on the spread of Japanese Knotweed in riparian zones.', '2023-04-12', '2023-09-10'),
('INV005', 'Nitrate Leaching in Grasslands', 'Measuring nitrogen runoff after intensive fertilization.', '2023-05-20', '2023-10-05'),
('INV006', 'Urban Soil Contamination', 'Heavy metal analysis in community gardens.', '2023-06-15', '2023-11-15'),
('INV007', 'Forest Canopy Biodiversity', 'Arthropod diversity in old-growth beech forests.', '2023-07-01', '2023-12-01'),
('INV008', 'Maize Phenotyping Experiment', 'High-throughput imaging of maize growth stages.', '2023-08-10', '2024-01-15'),
('INV009', 'Groundwater Quality Assessment', 'Monitoring pesticides in agricultural watersheds.', '2023-09-05', '2024-02-10'),
('INV010', 'Alpine Meadow Phenology', 'Climate change impacts on flowering times in the Alps.', '2023-10-12', '2024-03-20');

-- Add some contacts
INSERT INTO "vContact" (first_name, last_name, email, affiliation, investigation_ref) VALUES
('Jane', 'Doe', 'jane.doe@example.org', 'University of Soil Science', 'INV001'),
('John', 'Smith', 'john.smith@example.org', 'Cereal Research Institute', 'INV002');

-- Add some studies
INSERT INTO "vStudy" (identifier, title, description_text, investigation_ref) VALUES
('STU001', 'Bacterial Profiling', '16S rRNA sequencing of soil samples.', 'INV001'),
('STU002', 'Drought Stress Assay', 'Greenhouse experiment with controlled watering.', 'INV002');

-- Add some assays
INSERT INTO "vAssay" (identifier, measurement_type_term, technology_type_term, investigation_ref, study_ref) VALUES
('ASS001', 'DNA Sequencing', 'Illumina MiSeq', 'INV001', '["STU001"]'),
('ASS002', 'Phenotyping', 'Infrared Imaging', 'INV002', '["STU002"]');
