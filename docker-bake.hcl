variable "REGISTRY" {
    default = "ghcr.io/nishit-g"
}

variable "VERSION" {
    default = "latest"
}

# Base images
target "base-common" {
    dockerfile = "base/common.dockerfile"
    contexts = {
        scripts = "./base/scripts"
        manifests = "./manifests"  # Add manifests context
    }
    tags = ["${REGISTRY}/aiclipse-base-common:${VERSION}"]
    platforms = ["linux/amd64"]
}

target "base-rtx4090" {
    dockerfile = "base/rtx4090.dockerfile"
    contexts = {
        scripts = "./base/scripts"
        manifests = "./manifests"  # Add manifests context
    }
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-common"]
}

target "base-rtx5090" {
    dockerfile = "base/rtx5090.dockerfile"
    contexts = {
        scripts = "./base/scripts"
        manifests = "./manifests"  # Add manifests context
    }
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-common"]
}

# Template builds
target "headshots-4090" {
    dockerfile = "templates/headshots/Dockerfile"
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-headshots:rtx4090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx4090"]
}

target "headshots-5090" {
    dockerfile = "templates/headshots/Dockerfile"
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-headshots:rtx5090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx5090"]
}

# Build groups
group "bases" {
    targets = ["base-common", "base-rtx4090", "base-rtx5090"]
}

group "headshots" {
    targets = ["headshots-4090", "headshots-5090"]
}

group "all" {
    targets = ["bases", "headshots"]
}
