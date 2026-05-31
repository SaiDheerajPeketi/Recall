# Resolved issue: IVFFlat memory check on an empty table

## Reported problem

A public pgvector issue documented an IVFFlat index build on an empty or very small table failing because the reported memory requirement exceeded `maintenance_work_mem`. The reproduction used pgvector 0.8.4 with PostgreSQL 17, 1,536-dimensional vectors, 300 lists, and a 64 MB maintenance setting. The report contrasted this with earlier behavior that created the index while warning that too little data would produce low recall.

## Resolution boundary

The issue was closed after project changes addressed the regression. For support work, do not infer that every IVFFlat memory error has the same cause. Confirm the installed pgvector and PostgreSQL versions, vector dimensions, number of lists, table row count, exact error text, container or package tag, and `maintenance_work_mem`. Floating image tags can change the extension version between builds, so record the resolved image digest or explicit version.

## Safe actions

For an empty-table migration, prefer creating IVFFlat after representative data is loaded because the index requires training and an index built with too little data can have poor recall. If a schema tool requires the index up front, pin a known compatible pgvector version and validate the migration in a staging copy before production. Increasing `maintenance_work_mem` requires a capacity check because parallel maintenance workers can multiply memory use.

Collect the minimal reproduction and compare it against the current release notes before proposing a downgrade or upgrade. If the error persists on a fixed version or the memory estimate is unexplained, escalate with the reproduction rather than repeatedly increasing memory.

