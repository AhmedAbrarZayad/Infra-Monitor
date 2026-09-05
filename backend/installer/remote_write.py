"""Minimal Prometheus Remote Write v1 protobuf codec.

The descriptors mirror the identity/sample portion of Prometheus' official
prompb schema. Protobuf preserves unknown fields, so exemplars, histograms, and
metadata survive a decode/re-encode even though this gateway only edits labels.
"""

import re

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _message_class(pool, name):
    descriptor = pool.FindMessageTypeByName(name)
    if hasattr(message_factory, "GetMessageClass"):
        return message_factory.GetMessageClass(descriptor)
    return message_factory.MessageFactory(pool).GetPrototype(descriptor)


def _build_classes():
    file_descriptor = descriptor_pb2.FileDescriptorProto()
    file_descriptor.name = "prompb/remote_write_gateway.proto"
    file_descriptor.package = "prometheus"
    file_descriptor.syntax = "proto3"

    label = file_descriptor.message_type.add()
    label.name = "Label"
    for number, name in ((1, "name"), (2, "value")):
        field = label.field.add()
        field.name = name
        field.number = number
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    sample = file_descriptor.message_type.add()
    sample.name = "Sample"
    value = sample.field.add()
    value.name = "value"
    value.number = 1
    value.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    value.type = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE
    timestamp = sample.field.add()
    timestamp.name = "timestamp"
    timestamp.number = 2
    timestamp.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    timestamp.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64

    timeseries = file_descriptor.message_type.add()
    timeseries.name = "TimeSeries"
    for number, name, type_name in (
        (1, "labels", ".prometheus.Label"),
        (2, "samples", ".prometheus.Sample"),
    ):
        field = timeseries.field.add()
        field.name = name
        field.number = number
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
        field.type_name = type_name

    write_request = file_descriptor.message_type.add()
    write_request.name = "WriteRequest"
    field = write_request.field.add()
    field.name = "timeseries"
    field.number = 1
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = ".prometheus.TimeSeries"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_descriptor)
    return (
        _message_class(pool, "prometheus.WriteRequest"),
        _message_class(pool, "prometheus.TimeSeries"),
    )


WriteRequest, TimeSeries = _build_classes()

RESERVED_IDENTITY_LABELS = {
    "organization_id",
    "server_id",
    "vm_account_id",
    "vm_project_id",
    "service_id",
}

SERVICE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")


def service_metadata(write_request):
    """Return validated service names and optional ports found in series."""

    discovered = {}
    for series in write_request.timeseries:
        labels = {label.name: label.value for label in series.labels}
        name = (
            labels.get("service_name")
            or labels.get("container_label_monitoring_service_name")
            or ""
        ).strip()
        if not SERVICE_NAME.fullmatch(name):
            continue
        port_value = labels.get("service_port", "")
        try:
            port = int(port_value) if port_value else None
        except ValueError:
            port = None
        if port is not None and not 1 <= port <= 65535:
            port = None
        discovered[name] = port
    return discovered


def service_health_observations(write_request):
    """Return explicit application scrape health grouped by validated service name."""

    observations = {}
    for series in write_request.timeseries:
        labels = {label.name: label.value for label in series.labels}
        name = (
            labels.get("service_name")
            or labels.get("container_label_monitoring_service_name")
            or ""
        ).strip()
        if not SERVICE_NAME.fullmatch(name) or labels.get("__name__") != "up":
            continue
        if not series.samples:
            continue
        healthy = bool(series.samples[-1].value > 0)
        previous = observations.get(name)
        observations[name] = healthy if previous is None else previous and healthy
    return observations


def overwrite_identity(write_request, *, organization_id, server_id, service_ids=None):
    """Remove edge-controlled identity and apply credential-derived labels."""

    trusted = {
        "organization_id": str(organization_id),
        "server_id": str(server_id),
    }
    service_ids = service_ids or {}
    for series in write_request.timeseries:
        original = {label.name: label.value for label in series.labels}
        service_name = (
            original.get("service_name")
            or original.get("container_label_monitoring_service_name")
        )
        labels = [
            (label.name, label.value)
            for label in series.labels
            if label.name not in RESERVED_IDENTITY_LABELS
        ]
        labels.extend(trusted.items())
        if service_name in service_ids:
            labels.append(("service_id", str(service_ids[service_name])))
        labels.sort(key=lambda item: item[0])
        del series.labels[:]
        for name, value in labels:
            label = series.labels.add()
            label.name = name
            label.value = value
