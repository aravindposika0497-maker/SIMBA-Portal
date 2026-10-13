-- Least-privilege grants for the portal's Databricks service principal.
-- Run as a catalog owner / metastore admin in a SQL editor.
--
-- 1. Create the service principal: Workspace settings > Identity and access > Service principals > Add.
--    Generate an OAuth secret for it (client id + secret) and store BOTH in AWS Secrets Manager as
--    {"client_id": "...", "client_secret": "..."}. Do not paste the secret anywhere else.
-- 2. Give it "Can use" on the SQL Warehouse: SQL Warehouses > <warehouse> > Permissions.
-- 3. Replace <portal-sp-application-id> below with the service principal's Application ID (a UUID).
-- 4. If you want job runs on the Architecture page, give it "Can view" on those jobs.

-- Catalog + schema visibility (read-only)
GRANT USE CATALOG ON CATALOG simba_data_poc TO `<portal-sp-application-id>`;
GRANT USE SCHEMA ON SCHEMA simba_data_poc.bronze TO `<portal-sp-application-id>`;
GRANT USE SCHEMA ON SCHEMA simba_data_poc.silver TO `<portal-sp-application-id>`;
GRANT USE SCHEMA ON SCHEMA simba_data_poc.gold   TO `<portal-sp-application-id>`;

-- SELECT is needed for row counts, DESCRIBE HISTORY and the Kafka events table.
-- If you prefer not to give SELECT on whole schemas, grant it per table instead and set
-- SIMBA_ROW_COUNTS=false (the portal will then show schema metadata without counts).
GRANT SELECT ON SCHEMA simba_data_poc.bronze TO `<portal-sp-application-id>`;
GRANT SELECT ON SCHEMA simba_data_poc.silver TO `<portal-sp-application-id>`;
GRANT SELECT ON SCHEMA simba_data_poc.gold   TO `<portal-sp-application-id>`;

-- Lineage (Unity Catalog system tables). The `access` system schema must be enabled by an account admin.
GRANT USE CATALOG ON CATALOG system TO `<portal-sp-application-id>`;
GRANT USE SCHEMA ON SCHEMA system.access TO `<portal-sp-application-id>`;
GRANT SELECT ON TABLE system.access.table_lineage  TO `<portal-sp-application-id>`;
GRANT SELECT ON TABLE system.access.column_lineage TO `<portal-sp-application-id>`;

-- NOT granted on purpose: MODIFY, CREATE, MANAGE, ALL PRIVILEGES.
-- Note: information_schema.*_privileges only lists grants the principal is allowed to see. Without
-- MANAGE/ownership the Security & Governance page may be incomplete; it says so on the page.
-- Do not grant MANAGE just to fill that page — agree the approach with the platform owner first.

-- ---------------------------------------------------------------------------
-- Masked sample views (for SIMBA_SAMPLE_TABLES). Example shape only — replace the
-- column list with REAL columns from the RedApp extract once it has been validated.
-- ---------------------------------------------------------------------------
-- CREATE SCHEMA IF NOT EXISTS simba_data_poc.portal;
-- CREATE OR REPLACE VIEW simba_data_poc.portal.sample_<dataset> AS
--   SELECT <non-sensitive columns>, sha2(<id column>, 256) AS <id column>_hash
--   FROM simba_data_poc.bronze.<dataset>;
-- GRANT USE SCHEMA ON SCHEMA simba_data_poc.portal TO `<portal-sp-application-id>`;
-- GRANT SELECT ON VIEW simba_data_poc.portal.sample_<dataset> TO `<portal-sp-application-id>`;
