# Product-local Buildx Bake file (NOT synced). Target name must match
# reusable-build `components` matrix entry ("sql_to_arc").
#
# Version pins: do NOT default PYTHON_VERSION / UV_VERSION / PIP_VERSION /
# ALPINE_* / PYINSTALLER_VERSION here — inject from versions.env (reusable-build
# and scripts/run-container-structure-test.sh do this).

variable "APP_VERSION" {
  default = "0.0.0"
}

variable "PYTHON_VERSION" {}
variable "ALPINE_VERSION" {}
variable "ALPINE_MINOR" {}
variable "PIP_VERSION" {}
variable "UV_VERSION" {}
variable "PYINSTALLER_VERSION" {}

variable "IMAGE_TAG" {
  default = "sql-to-arc:test"
}

target "sql_to_arc-base" {
  context    = "."
  dockerfile = "docker/Dockerfile.product-app.base"
  target     = "export-binaries"
  args = {
    APP_VERSION            = APP_VERSION
    PYTHON_VERSION         = PYTHON_VERSION
    ALPINE_MINOR           = ALPINE_MINOR
    PIP_VERSION            = PIP_VERSION
    UV_VERSION             = UV_VERSION
    PYINSTALLER_VERSION    = PYINSTALLER_VERSION
    UV_BUILD_PACKAGES      = "sql_to_arc"
    BINARY_NAME            = "sql_to_arc"
    PYINSTALLER_IMPORT     = "middleware.sql_to_arc"
    BUILDER_APK_PACKAGES   = "unixodbc-dev"
    EXTRA_PYINSTALLER_ARGS = "--copy-metadata sql_to_arc --copy-metadata fairagro-middleware-api-client --copy-metadata fairagro-middleware-shared"
  }
}

target "sql_to_arc" {
  context    = "."
  dockerfile = "docker/Dockerfile.sql_to_arc"
  contexts = {
    export_bins = "target:sql_to_arc-base"
  }
  args = {
    ALPINE_VERSION = ALPINE_VERSION
    RUNTIME_USER   = "sql_to_arc"
  }
  tags      = [IMAGE_TAG]
  platforms = ["linux/amd64"]
}
