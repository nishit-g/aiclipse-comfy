variable "REGISTRY" {
  default = "ghcr.io/nishit-g"
}

variable "VERSION" {
  default = "latest"
}

# Common configuration for all targets
target "_common" {
  platforms = ["linux/amd64"]
}

# Base images
target "base-common" {
  inherits = ["_common"]
  dockerfile = "base/common.dockerfile"
  context = "."
  tags = ["${REGISTRY}/aiclipse-base-common:${VERSION}"]
  contexts = {
    manifests = "./manifests"
  }
}

target "base-rtx4090" {
  inherits = ["_common"]
  dockerfile = "base/rtx4090.dockerfile"
  context = "."
  tags = ["${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"]
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
  contexts = {
    scripts = "./base/scripts"
    manifests = "./manifests"
  }
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
  }
}

# SD 1.5 Basic Template builds
target "sd15-basic-rtx4090" {  # Match workflow expectation
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/sd15-basic"
  tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx4090-${VERSION}"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
  }
}

target "sd15-basic-rtx5090" {  # Match workflow expectation
  inherits = ["_common"]
  dockerfile = "Dockerfile"
  context = "templates/sd15-basic"
  tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx5090-${VERSION}"]
  args = {
    BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
  }
}

# Build groups
group "bases" {
  targets = ["base-common", "base-rtx4090", "base-rtx5090"]
}

group "sd15-basic" {
  targets = ["sd15-basic-4090", "sd15-basic-5090"]
}

group "all" {
  targets = ["base-common", "base-rtx4090", "base-rtx5090", "sd15-basic-4090", "sd15-basic-5090"]
}
