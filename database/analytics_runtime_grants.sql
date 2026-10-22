-- Trusted operator after migration 011. Read-only, role/owner/release-scoped function.
GRANT EXECUTE ON FUNCTION mcq.analytics_data(uuid,text,uuid,integer,integer,boolean) TO :"runtime_role";
