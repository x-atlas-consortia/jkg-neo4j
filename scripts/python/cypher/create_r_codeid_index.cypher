// Creates a range index on the codeid property
CREATE INDEX code_codeid IF NOT EXISTS
FOR ()-[r:CODE]-()
ON (r.codeid);