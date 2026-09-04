def generate_alloy_config(*, ingestion_url, organization_id, server_id, docker_available):
    """Build the Alloy configuration returned once during enrollment."""

    collectors = f'''
prometheus.exporter.unix "host" {{
}}

prometheus.scrape "host" {{
  targets    = prometheus.exporter.unix.host.targets
  forward_to = [prometheus.relabel.identity.receiver]
}}
'''

    if docker_available:
        collectors += '''

prometheus.exporter.cadvisor "docker" {
  docker_host = "unix:///var/run/docker.sock"
  allowlisted_container_labels = [
    "monitoring.enabled",
    "monitoring.service_name",
  ]
}

prometheus.scrape "docker" {
  targets    = prometheus.exporter.cadvisor.docker.targets
  forward_to = [prometheus.relabel.identity.receiver]
}

// Discover application /metrics endpoints only on explicitly enabled
// containers. Docker label dots are exposed by Alloy as underscores.
discovery.docker "applications" {
  host = "unix:///var/run/docker.sock"
}

discovery.relabel "applications" {
  targets = discovery.docker.applications.targets

  rule {
    action        = "keep"
    source_labels = ["__meta_docker_container_label_monitoring_enabled"]
    regex         = "true"
  }

  rule {
    action        = "keep"
    source_labels = ["__meta_docker_container_label_monitoring_service_name"]
    regex         = ".+"
  }

  rule {
    action        = "keep"
    source_labels = ["__meta_docker_container_label_monitoring_metrics_port"]
    regex         = "[0-9]+"
  }

  rule {
    source_labels = ["__meta_docker_network_ip", "__meta_docker_container_label_monitoring_metrics_port"]
    separator     = ":"
    regex         = "(.+):([0-9]+)"
    replacement   = "$1:$2"
    target_label  = "__address__"
  }

  rule {
    source_labels = ["__meta_docker_container_label_monitoring_metrics_path"]
    regex         = "(.+)"
    replacement   = "$1"
    target_label  = "__metrics_path__"
  }

  rule {
    source_labels = ["__meta_docker_container_label_monitoring_service_name"]
    target_label  = "service_name"
  }

  rule {
    source_labels = ["__meta_docker_container_label_monitoring_metrics_port"]
    target_label  = "service_port"
  }
}

prometheus.scrape "applications" {
  targets         = discovery.relabel.applications.output
  metrics_path    = "/metrics"
  scrape_interval = "15s"
  forward_to      = [prometheus.relabel.identity.receiver]
}
'''

    return (
        collectors
        + f'''

// These edge labels aid debugging, but the ingestion gateway always replaces
// them with identity derived from the server credential.
prometheus.relabel "identity" {{
  forward_to = [prometheus.remote_write.infra_monitor.receiver]

  rule {{
    target_label = "organization_id"
    replacement  = "{organization_id}"
  }}

  rule {{
    target_label = "server_id"
    replacement  = "{server_id}"
  }}
}}

prometheus.remote_write "infra_monitor" {{
  endpoint {{
    url = "{ingestion_url}"

    authorization {{
      type             = "Bearer"
      credentials_file = "/etc/alloy/credential"
    }}
  }}
}}
'''
    ).strip() + "\n"
