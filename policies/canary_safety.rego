package swiftdeploy.canary

import future.keywords.if
import future.keywords.contains

default allow := false

allow if {
    count(violations) == 0
}

violations contains msg if {
    input.error_rate > data.thresholds.max_error_rate
    msg := sprintf("Error rate %.2f%% exceeds maximum %.2f%%", [input.error_rate * 100, data.thresholds.max_error_rate * 100])
}

violations contains msg if {
    input.p99_latency_ms > data.thresholds.max_p99_latency_ms
    msg := sprintf("P99 latency %dms exceeds maximum %dms", [input.p99_latency_ms, data.thresholds.max_p99_latency_ms])
}

reason := {
    "allow": allow,
    "violations": violations,
    "domain": "canary_safety"
}
