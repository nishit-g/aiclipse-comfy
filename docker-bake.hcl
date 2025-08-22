variable "REGISTRY" {
    default = "ghcr.io/nishit-g"
}

variable "VERSION" {
    default = "latest"
}

# Base images
target "base-common" {
    dockerfile = "base/common.dockerfile"
    context = "."
    contexts = {
        manifests = "./manifests"
    }
    tags = ["${REGISTRY}/aiclipse-base-common:${VERSION}"]
    platforms = ["linux/amd64"]
}

target "base-rtx4090" {
    dockerfile = "base/rtx4090.dockerfile"
    context = "."
    contexts = {
        scripts = "./base/scripts"
        manifests = "./manifests"
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
    context = "."
    contexts = {
        scripts = "./base/scripts"
        manifests = "./manifests"
    }
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-common:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-common"]
}

# SD 1.5 Basic Template builds
target "sd15-basic-4090" {
    dockerfile = "templates/sd15-basic/Dockerfile"
    context = "templates/sd15-basic"
    contexts = {
        base = "."
    }
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx4090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx4090"]
}

target "sd15-basic-5090" {
    dockerfile = "templates/sd15-basic/Dockerfile"
    context = "templates/sd15-basic"
    contexts = {
        base = "."
    }
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-sd15-basic:rtx5090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx5090"]
}

# Build groups
group "bases" {
    targets = ["base-common", "base-rtx4090", "base-rtx5090"]
}

group "sd15-basic" {
    targets = ["sd15-basic-4090", "sd15-basic-5090"]
}

group "all" {
    targets = ["bases", "sd15-basic"]
}
