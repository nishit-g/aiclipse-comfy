variable "REGISTRY" {
  default = "ghcr.io/nishit-g"
}

variable "VERSION" {
  default = "latest"
}

variable "CACHE_TYPE" {
  default = "registry"
}

# Common configuration for all targets
target "_common" {
  platforms = ["linux/amd64"]
}

# Base images with DYNAMIC cache
target "base-common" {
  inherits = ["_common"]
  dockerfile = "base/common.dockerfile"
  context = "."
  tags = ["${REGISTRY}/aiclipse-base-common:${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-common:cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-common:cache,mode=max"]
  contexts = {
    manifests = "./manifests"
  }
}

target "base-rtx4090" {
  inherits = ["_common"]
  dockerfile = "base/rtx4090.dockerfile"
  context = "."
  tags = ["${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-rtx4090:cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-rtx4090:cache,mode=max"]
  contexts = {
    scripts = "./base/scripts"
    manifests = "./manifests"
  }
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
  }
}

target "base-rtx5090" {
  inherits = ["_common"]
  dockerfile = "base/rtx5090.dockerfile"
  context = "."
  tags = ["${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-rtx5090:cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-base-rtx5090:cache,mode=max"]
  contexts = {
    scripts = "./base/scripts"
    manifests = "./manifests"
  }
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
  }
}

# Templates with DYNAMIC cache
target "sd15-basic-rtx4090" {
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/sd15-basic"
  tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx4090-${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-sd15-basic:rtx4090-cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-sd15-basic:rtx4090-cache,mode=max"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
  }
}

target "sd15-basic-rtx5090" {
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/sd15-basic"
  tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx5090-${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-sd15-basic:rtx5090-cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-sd15-basic:rtx5090-cache,mode=max"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
  }
}

target "boomboom-rtx5090" {
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/boomboom"
  tags = ["${REGISTRY}/aiclipse-boomboom:rtx5090-${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-boomboom:rtx5090-cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-boomboom:rtx5090-cache,mode=max"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
  }
}

target "qwen-multi-edit-rtx5090" {
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/qwen-multi-edit"
  tags = ["${REGISTRY}/aiclipse-qwen-multi-edit:rtx5090-${VERSION}"]
  cache-from = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-qwen-multi-edit:rtx5090-cache"]
  cache-to = ["type=${CACHE_TYPE},ref=${REGISTRY}/aiclipse-qwen-multi-edit:rtx5090-cache,mode=max"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
  }
}

# Build groups
group "bases" {
  targets = ["base-common", "base-rtx4090", "base-rtx5090"]
}

group "sd15-basic" {
  targets = ["sd15-basic-rtx4090", "sd15-basic-rtx5090"]
}

group "boomboom" {
  targets = ["boomboom-rtx5090"]
}

group "qwen-multi-edit" {
  targets = ["qwen-multi-edit-rtx5090"]
}

group "all" {
  targets = ["base-common", "base-rtx4090", "base-rtx5090", "sd15-basic-rtx4090", "sd15-basic-rtx5090", "boomboom-rtx5090", "qwen-multi-edit-rtx5090"]
}
