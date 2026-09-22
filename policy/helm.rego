package main

import rego.v1

# Only first-party workloads are release artifacts. Supporting third-party
# services are governed independently and are deliberately excluded here.
managed_workloads := {"api", "frontend", "nginx"}

deny contains msg if {
  input.kind == "Deployment"
  some workload in managed_workloads
  input.metadata.name == workload
  some container in input.spec.template.spec.containers
  not contains(container.image, "@sha256:")
  msg := sprintf("%s/%s must use an immutable image digest", [input.metadata.name, container.name])
}
