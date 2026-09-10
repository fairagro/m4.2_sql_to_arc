# Product-local Bake targets for container-structure-test (shared CST runner).
# Full product-app Bake base adoption is Wave C; this keeps pre-push CST green.

target "sql_to_arc" {
  context    = "."
  dockerfile = "docker/Dockerfile.sql_to_arc"
  tags       = ["sql-to-arc:test"]
}
