from datetime import timedelta
import re

from django.db import connection, transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization, OrganizationMembership, UserPreference
from alert.models import Alert
from incident.models import Incident, IncidentAlert, IncidentUpdate
from log.models import LogEntry
from ml_model.models import AnomalyDetection
from servers.models import Servers, Service
from servers.services import InvalidMetricError, VictoriaMetricsQueryAdapter


def membership(request, organization_id, roles=None):
    org = get_object_or_404(Organization, pk=organization_id)
    member = get_object_or_404(OrganizationMembership, organization=org, user=request.user, approved=True)
    if roles and member.role not in roles:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("You do not have permission to perform this action.")
    return org, member


def page(request, queryset, render):
    paginator = LimitOffsetPagination()
    items = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([render(item) for item in items])


def filter_time(qs, request, field):
    start=parse_datetime(request.query_params.get("from", "")); end=parse_datetime(request.query_params.get("to", ""))
    if start: qs=qs.filter(**{f"{field}__gte":start})
    if end: qs=qs.filter(**{f"{field}__lte":end})
    return qs


def user_data(user):
    if not user:
        return None
    return {"id": user.id, "username": user.username, "email": user.email,
            "first_name": user.first_name, "last_name": user.last_name}


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ["notifications_enabled", "refresh_interval_seconds", "timezone", "theme", "default_environment", "updated_at"]
        read_only_fields = ["updated_at"]

    def validate_refresh_interval_seconds(self, value):
        if value < 5 or value > 3600:
            raise serializers.ValidationError("Must be between 5 and 3600 seconds.")
        return value


class PreferencesView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, user):
        return UserPreference.objects.get_or_create(user_id=user)[0]
    def get(self, request):
        return Response(PreferenceSerializer(self.get_object(request.user)).data)
    def patch(self, request):
        serializer = PreferenceSerializer(self.get_object(request.user), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True); serializer.save()
        return Response(serializer.data)


def latest_metric(server, code, service=None):
    return VictoriaMetricsQueryAdapter().latest(server=server, code=code, service=service)


def metric_value(server, code, service=None):
    result = latest_metric(server, code, service)
    item = result["point"]
    if item is None:
        return None
    return {"value": item["value"], "unit": item["unit"], "recorded_at": item["recorded_at"], "labels": item["labels"]}


def metric_history(server, code, service=None, limit=30):
    result = VictoriaMetricsQueryAdapter().range(server=server, code=code, service=service)
    return [point["value"] for point in result["points"][-limit:]]


def server_data(item):
    return {"id": item.server_id, "name": item.name, "host_name": item.host_name,
            "environment": item.environment, "os_type": item.os_type, "status": item.status,
            "last_seen_at": item.last_seen_at, "registered_at": item.registered_at,
            "alert_count": Alert.objects.filter(organization=item.organization, server_id=item, state__in=["ACTIVE", "ACKNOWLEDGED"]).count(),
            "metrics": {code: metric_value(item, code) for code in ["cpu_r", "mem_u", "disk_u"]},
            "service_count": item.services.count(),
            "cpu_history": metric_history(item, "cpu_r")}


def service_data(item):
    return {"id": item.service_id, "server_id": item.server_id_id, "service_name": item.service_name,
            "display_name": item.display_name, "status": item.status, "port": item.port,
            "last_reported_at": item.last_reported_at,
            "alert_count": Alert.objects.filter(organization=item.server_id.organization, service_id=item, state__in=["ACTIVE", "ACKNOWLEDGED"]).count()}


class ServerListView(APIView):
    def get(self, request, organization_id):
        org, _ = membership(request, organization_id)
        qs = Servers.objects.filter(organization=org)
        q = request.query_params.get("q"); state = request.query_params.get("status"); env = request.query_params.get("environment")
        if q: qs = qs.filter(Q(name__icontains=q) | Q(host_name__icontains=q))
        if state: qs = qs.filter(status=state.upper())
        if env: qs = qs.filter(environment__iexact=env)
        return page(request, qs, server_data)


class ServerDetailView(APIView):
    def get_object(self, org, pk): return get_object_or_404(Servers, organization=org, pk=pk)
    def get(self, request, organization_id, server_id):
        org, _ = membership(request, organization_id); return Response(server_data(self.get_object(org, server_id)))
    def patch(self, request, organization_id, server_id):
        org, _ = membership(request, organization_id, {"OWNER", "ADMIN"}); obj = self.get_object(org, server_id)
        allowed = {"name", "environment"}
        unknown = set(request.data) - allowed
        if unknown: return Response({key: ["This field cannot be changed here."] for key in unknown}, status=400)
        for key in allowed & set(request.data): setattr(obj, key, request.data[key])
        obj.save(update_fields=list(allowed & set(request.data))); return Response(server_data(obj))


class ServerHealthView(APIView):
    def get(self, request, organization_id, server_id):
        org, _ = membership(request, organization_id); obj = get_object_or_404(Servers, organization=org, pk=server_id)
        return Response({"server_id": obj.server_id, "status": obj.status, "last_seen_at": obj.last_seen_at,
                         "metrics": {code: metric_value(obj, code) for code in ["cpu_r", "load_1", "load_5", "mem_u", "disk_q", "disk_r", "disk_w", "disk_u", "eth1_fi", "eth1_fo", "tcp_timeouts"]},
                         "active_alerts": Alert.objects.filter(organization=org, server_id=obj, state__in=["ACTIVE", "ACKNOWLEDGED"]).count()})


class MetricRangeView(APIView):
    service_scoped = False
    def get(self, request, organization_id, server_id=None, service_id=None):
        org, _ = membership(request, organization_id)
        service = None
        if self.service_scoped:
            service = get_object_or_404(Service, server_id__organization=org, pk=service_id); server = service.server_id
        else: server = get_object_or_404(Servers, organization=org, pk=server_id)
        code = request.query_params.get("metric")
        if not code: return Response({"metric": ["This query parameter is required."]}, status=400)
        raw_start = request.query_params.get("from", "")
        raw_end = request.query_params.get("to", "")
        start = parse_datetime(raw_start); end = parse_datetime(raw_end)
        if raw_start and start is None:
            return Response({"from": ["Use a valid ISO-8601 timestamp."]}, status=400)
        if raw_end and end is None:
            return Response({"to": ["Use a valid ISO-8601 timestamp."]}, status=400)
        try:
            result = VictoriaMetricsQueryAdapter().range(
                server=server,
                code=code,
                service=service,
                start=start,
                end=end,
                step=request.query_params.get("step"),
            )
        except (InvalidMetricError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({
            "metric": code,
            "unit": result["unit"],
            "available": result["available"],
            "availability": result["availability"],
            "points": [
                {
                    "timestamp": point["timestamp"],
                    "value": point["value"],
                    "unit": point["unit"],
                    "labels": point["labels"],
                }
                for point in result["points"]
            ],
        })


class ServiceListView(APIView):
    def get(self, request, organization_id, server_id):
        org, _ = membership(request, organization_id); server = get_object_or_404(Servers, organization=org, pk=server_id)
        qs = Service.objects.filter(server_id=server)
        if request.query_params.get("status"): qs = qs.filter(status=request.query_params["status"].upper())
        return page(request, qs, service_data)


class ServiceDetailView(APIView):
    def get_obj(self, org, pk): return get_object_or_404(Service, server_id__organization=org, pk=pk)
    def get(self, request, organization_id, service_id):
        org, _ = membership(request, organization_id); return Response(service_data(self.get_obj(org, service_id)))
    def patch(self, request, organization_id, service_id):
        org, _ = membership(request, organization_id, {"OWNER", "ADMIN"}); obj = self.get_obj(org, service_id)
        if set(request.data) - {"display_name"}: return Response({"detail": "Only display_name may be changed."}, status=400)
        obj.display_name = request.data.get("display_name", obj.display_name); obj.save(update_fields=["display_name"])
        return Response(service_data(obj))


class ServiceHealthView(APIView):
    def get(self, request, organization_id, service_id):
        org, _ = membership(request, organization_id); obj = get_object_or_404(Service, server_id__organization=org, pk=service_id)
        return Response({**service_data(obj), "metrics": {code: metric_value(obj.server_id, code, obj) for code in ["cpu_r", "mem_u", "disk_u"]}})


def alert_data(x):
    return {"id": x.alert_id, "server_id": x.server_id_id, "service_id": x.service_id_id, "detection_id": x.detection_id_id,
            "title": x.title, "description": x.description, "category": x.category, "severity": x.severity,
            "state": x.state, "fingerprint": x.fingerprint, "triggered_at": x.triggered_at,
            "acknowledged_at": x.acknowledged_at, "cleared_at": x.cleared_at, "acknowledged_by": user_data(x.acknowledged_by)}


class AlertListView(APIView):
    def get(self, request, organization_id):
        org, _ = membership(request, organization_id); qs = Alert.objects.filter(organization=org)
        for key in ["state", "severity", "server_id", "service_id"]:
            if request.query_params.get(key): qs = qs.filter(**{key: request.query_params[key].upper() if key in {"state", "severity"} else request.query_params[key]})
        if request.query_params.get("q"): qs = qs.filter(Q(title__icontains=request.query_params["q"]) | Q(description__icontains=request.query_params["q"]))
        return page(request, filter_time(qs,request,"triggered_at"), alert_data)


class AlertDetailView(APIView):
    def get(self, request, organization_id, alert_id):
        org, _ = membership(request, organization_id); return Response(alert_data(get_object_or_404(Alert, organization=org, pk=alert_id)))


class AlertActionView(APIView):
    resolve = False
    def post(self, request, organization_id, alert_id):
        org, _ = membership(request, organization_id, {"OWNER", "ADMIN"} if self.resolve else None)
        with transaction.atomic():
            obj = get_object_or_404(Alert.objects.select_for_update(), organization=org, pk=alert_id)
            if self.resolve:
                if obj.state == Alert.State.RESOLVED: return Response(alert_data(obj))
                obj.state=Alert.State.RESOLVED; obj.cleared_at=timezone.now(); obj.cleared_by=request.user
                obj.save(update_fields=["state", "cleared_at", "cleared_by"])
            else:
                if obj.state == Alert.State.RESOLVED: return Response({"detail":"Resolved alerts cannot be acknowledged.","code":"alert_resolved"}, status=409)
                if obj.state != Alert.State.ACKNOWLEDGED:
                    obj.state=Alert.State.ACKNOWLEDGED; obj.acknowledged_at=timezone.now(); obj.acknowledged_by=request.user
                    obj.save(update_fields=["state", "acknowledged_at", "acknowledged_by"])
        return Response(alert_data(obj))


def log_data(x): return {"id":x.log_id,"server_id":x.server_id_id,"service_id":x.service_id_id,"source":x.source,"level":x.log_level,"message":x.message,"metadata":x.metadata,"logged_at":x.logged_at,"ingested_at":x.ingested_at}

class LogListView(APIView):
    def get(self, request, organization_id):
        org,_=membership(request,organization_id); qs=LogEntry.objects.filter(organization=org)
        if request.query_params.get("q"): qs=qs.filter(Q(message__icontains=request.query_params["q"])|Q(source__icontains=request.query_params["q"]))
        for p,f in [("level","log_level"),("source","source"),("server_id","server_id"),("service_id","service_id")]:
            if request.query_params.get(p): qs=qs.filter(**{f:request.query_params[p]})
        return page(request,filter_time(qs,request,"logged_at"),log_data)

class LogDetailView(APIView):
    def get(self,request,organization_id,log_id):
        org,_=membership(request,organization_id); return Response(log_data(get_object_or_404(LogEntry,organization=org,pk=log_id)))


def incident_data(x):
    analysis = x.aianalysis_set.order_by("-created_at").first() if hasattr(x, "aianalysis_set") else None
    return {"id":x.incident_id,"code":x.incident_code,"server_id":x.server_id_id,"server":x.server_id.name if x.server_id else "",
            "service":"","environment":x.server_id.environment if x.server_id else "","title":x.title,"description":x.description,
            "category":x.category,"severity":x.severity,"status":x.status,"detected_at":x.detected_at,"acknowledged_at":x.acknowledged_at,
            "resolved_at":x.resolved_at,"resolution_notes":x.resolution_notes,"assigned_to":user_data(x.assigned_to),
            "ai_confidence": None if analysis is None else analysis.confidence_score}

class IncidentListView(APIView):
    def get(self,request,organization_id):
        org,_=membership(request,organization_id); qs=Incident.objects.filter(organization=org).select_related("assigned_to")
        if request.query_params.get("q"): qs=qs.filter(Q(title__icontains=request.query_params["q"])|Q(incident_code__icontains=request.query_params["q"]))
        for p in ["severity","status"]:
            if request.query_params.get(p): qs=qs.filter(**{p:request.query_params[p].upper()})
        if request.query_params.get("assigned_to"): qs=qs.filter(assigned_to_id=request.query_params["assigned_to"])
        return page(request,qs,incident_data)

class IncidentDetailView(APIView):
    def get(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id); return Response(incident_data(get_object_or_404(Incident,organization=org,pk=incident_id)))

def add_update(obj,user,action,old="",new="",comment=""):
    IncidentUpdate.objects.create(incident_id=obj,user_id=user,action=action,old_status=old,new_status=new,comment=comment)

class IncidentAcknowledgeView(APIView):
    def post(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id)
        with transaction.atomic():
            obj=get_object_or_404(Incident.objects.select_for_update(),organization=org,pk=incident_id)
            if not obj.acknowledged_at:
                old=obj.status; obj.acknowledged_at=timezone.now(); obj.status=Incident.Status.ACKNOWLEDGED; obj.save(update_fields=["acknowledged_at","status"]); add_update(obj,request.user,"ACKNOWLEDGED",old,obj.status)
        return Response(incident_data(obj))

class IncidentBulkAcknowledgeView(APIView):
    def post(self,request,organization_id):
        org,_=membership(request,organization_id); ids=request.data.get("incident_ids")
        if not isinstance(ids,list) or not ids: return Response({"incident_ids":["Provide a non-empty list."]},status=400)
        done=[]
        with transaction.atomic():
            for obj in Incident.objects.select_for_update().filter(organization=org,incident_id__in=ids):
                if not obj.acknowledged_at:
                    old=obj.status; obj.acknowledged_at=timezone.now(); obj.status=Incident.Status.ACKNOWLEDGED; obj.save(update_fields=["acknowledged_at","status"]); add_update(obj,request.user,"ACKNOWLEDGED",old,obj.status)
                done.append(str(obj.incident_id))
        return Response({"acknowledged":done,"not_found_count":len(set(map(str,ids))-set(done))})

class IncidentAssignView(APIView):
    self_assign=False
    def post(self,request,organization_id,incident_id): return self._change(request,organization_id,incident_id)
    def patch(self,request,organization_id,incident_id): return self._change(request,organization_id,incident_id)
    def _change(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id,None if self.self_assign else {"OWNER","ADMIN"}); target=request.user if self.self_assign else None
        if not self.self_assign and request.data.get("user_id") is not None:
            target_membership=get_object_or_404(OrganizationMembership,organization=org,user_id=request.data["user_id"],approved=True); target=target_membership.user
        with transaction.atomic():
            obj=get_object_or_404(Incident.objects.select_for_update(),organization=org,pk=incident_id); obj.assigned_to=target; obj.save(update_fields=["assigned_to"]); add_update(obj,request.user,"ASSIGNED",comment="" if target is None else str(target.id))
        return Response(incident_data(obj))

class IncidentStatusView(APIView):
    transitions={"NEW":{"ACKNOWLEDGED"},"ACKNOWLEDGED":{"INVESTIGATING","RESOLVED"},"INVESTIGATING":{"RESOLVED"},"RESOLVED":set()}
    def patch(self,request,organization_id,incident_id):
        org,member=membership(request,organization_id); target=str(request.data.get("status","")).upper()
        with transaction.atomic():
            obj=get_object_or_404(Incident.objects.select_for_update(),organization=org,pk=incident_id)
            if member.role not in {"OWNER","ADMIN"} and obj.assigned_to_id != request.user.id: return Response({"detail":"Only the assignee, owner, or admin may change status."},status=403)
            if target not in self.transitions.get(obj.status,set()): return Response({"detail":"Invalid status transition.","code":"invalid_incident_transition"},status=409)
            old=obj.status; obj.status=target
            if target=="ACKNOWLEDGED" and not obj.acknowledged_at: obj.acknowledged_at=timezone.now()
            if target=="RESOLVED": obj.resolved_at=timezone.now(); obj.resolution_notes=request.data.get("resolution_notes",obj.resolution_notes)
            obj.save(); add_update(obj,request.user,"STATUS_CHANGED",old,target,request.data.get("comment",""))
        return Response(incident_data(obj))

class IncidentUpdatesView(APIView):
    def get(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id); obj=get_object_or_404(Incident,organization=org,pk=incident_id)
        return page(request,obj.incidentupdate_set.select_related("user_id"),lambda x:{"id":x.update_id,"action":x.action,"old_status":x.old_status,"new_status":x.new_status,"comment":x.comment,"user":user_data(x.user_id),"created_at":x.created_at})

class IncidentFeedbackView(APIView):
    def post(self,request,organization_id,incident_id):
        org,member=membership(request,organization_id); obj=get_object_or_404(Incident,organization=org,pk=incident_id)
        if member.role not in {"OWNER","ADMIN"} and obj.assigned_to_id != request.user.id: return Response({"detail":"Only the assignee, owner, or admin may add feedback."},status=403)
        comment=str(request.data.get("comment","")).strip()
        if not comment:return Response({"comment":["This field is required."]},status=400)
        update=IncidentUpdate.objects.create(incident_id=obj,user_id=request.user,action="FEEDBACK",comment=comment)
        return Response({"id":update.update_id,"comment":update.comment,"created_at":update.created_at},status=201)

class IncidentAlertsView(APIView):
    def get(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id); obj=get_object_or_404(Incident,organization=org,pk=incident_id)
        return page(request,Alert.objects.filter(incidentalert__incident_id=obj,organization=org),alert_data)

class IncidentEvidenceView(APIView):
    def get(self,request,organization_id,incident_id):
        org,_=membership(request,organization_id); obj=get_object_or_404(Incident,organization=org,pk=incident_id)
        alerts=Alert.objects.filter(incidentalert__incident_id=obj,organization=org)
        logs=LogEntry.objects.filter(organization=org,server_id=obj.server_id)[:100] if obj.server_id else []
        anomalies=AnomalyDetection.objects.filter(organization=org,server_id=obj.server_id)[:100] if obj.server_id else []
        return Response({"incident_id":obj.incident_id,"alerts":[alert_data(x) for x in alerts],"logs":[log_data(x) for x in logs],"anomalies":[anomaly_data(x) for x in anomalies]})

def anomaly_data(x): return {"id":x.detection_id,"server_id":x.server_id_id,"service_id":x.service_id_id,"anomaly_score":x.anomaly_score,"confidence_score":x.confidence_score,"is_anomaly":x.is_anomaly,"feature_values":x.feature_values,"window_started_at":x.window_started_at,"window_ended_at":x.window_ended_at,"detected_at":x.detected_at}

class AnomalyListView(APIView):
    def get(self,request,organization_id):
        org,_=membership(request,organization_id); qs=AnomalyDetection.objects.filter(organization=org)
        for p in ["server_id","service_id","is_anomaly"]:
            if request.query_params.get(p) is not None:
                value=request.query_params[p]; value=value.lower()=="true" if p=="is_anomaly" else value; qs=qs.filter(**{p:value})
        return page(request,filter_time(qs,request,"detected_at"),anomaly_data)

class AnomalyDetailView(APIView):
    def get(self,request,organization_id,detection_id):
        org,_=membership(request,organization_id); return Response(anomaly_data(get_object_or_404(AnomalyDetection,organization=org,pk=detection_id)))

class OverviewView(APIView):
    def get(self,request,organization_id):
        org,_=membership(request,organization_id); servers=Servers.objects.filter(organization=org); env=request.query_params.get("environment")
        if env: servers=servers.filter(environment__iexact=env)
        incidents=Incident.objects.filter(organization=org).exclude(status="RESOLVED")
        alerts=Alert.objects.filter(organization=org).order_by("-triggered_at")[:10]
        attention=[]
        for code,label in [("cpu_r","HIGHEST CPU"),("mem_u","HIGHEST MEMORY"),("disk_u","HIGHEST DISK")]:
            candidates=[]
            for server in servers:
                metric=latest_metric(server,code)["point"]
                if metric and metric["unit"].lower() in {"percent","%","percentage"}: candidates.append((metric["value"],server,metric))
            if candidates:
                value,server,metric=max(candidates,key=lambda x:x[0]); attention.append({"label":label,"resource":server.name,"value":value,"unit":metric["unit"],"severity":"CRITICAL" if value>=90 else "WARNING" if value>=70 else "INFO"})
        return Response({"server_count":servers.count(),"open_incident_count":incidents.count(),"updated_at":timezone.now(),
            "fleet":{x:servers.filter(status=x).count() for x,_ in Servers.Status.choices},
            "critical_incidents":[incident_data(x) for x in incidents.filter(severity="CRITICAL")[:5]],
            "high_incidents":[incident_data(x) for x in incidents.filter(severity="HIGH")[:5]],"attention_items":attention,
            "alerts":[alert_data(x) for x in alerts],"platform_health":[{"component":"api","status":"HEALTHY"}],"telemetry_available":servers.filter(monitoring_connection__last_metric_at__isnull=False).exists()})

class AnalyticsView(APIView):
    def get(self,request,organization_id):
        org,_=membership(request,organization_id); now=timezone.now(); incidents=Incident.objects.filter(organization=org)
        resolved=incidents.filter(status="RESOLVED",resolved_at__isnull=False)
        durations=[(x.resolved_at-x.detected_at).total_seconds() for x in resolved if x.resolved_at]
        ack=[(x.acknowledged_at-x.detected_at).total_seconds() for x in incidents.filter(acknowledged_at__isnull=False)]
        def values(*codes):
            collected=[]
            for server in Servers.objects.filter(organization=org):
                for code in codes:
                    try: collected.extend(metric_history(server,code,limit=100))
                    except InvalidMetricError: continue
            return collected[-100:]
        return Response({"available":incidents.exists() or Servers.objects.filter(organization=org,monitoring_connection__last_metric_at__isnull=False).exists(),
            "metrics":{"mtta_seconds":sum(ack)/len(ack) if ack else None,"mttr_seconds":sum(durations)/len(durations) if durations else None,"open":incidents.exclude(status="RESOLVED").count(),"resolved_7d":resolved.filter(resolved_at__gte=now-timedelta(days=7)).count()},
            "series":{"cpu":values("cpu_r"),"memory":values("mem_u"),"latency":values("latency","request_latency"),"frequency":[],"opened":[],"resolved":[],"uptime":values("uptime")},
            "categories":dict(incidents.values_list("category").annotate(c=Count("incident_id"))),
            "servers":dict(incidents.filter(server_id__isnull=False).values_list("server_id__name").annotate(c=Count("incident_id"))),"insights":[]})

class LiveView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):return Response({"status":"ok"})
class ReadyView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        try:
            with connection.cursor() as cursor: cursor.execute("SELECT 1")
            return Response({"status":"ready","database":"ok"})
        except Exception:return Response({"status":"not_ready"},status=503)
class DependencyHealthView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        telemetry = "ok" if VictoriaMetricsQueryAdapter().healthy() else "unavailable"
        return Response({"database":"ok","telemetry":telemetry,"ml":"not_configured","gemini":"not_configured"})
class WorkerHealthView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):return Response({"status":"not_configured","workers":[]})

class LogBatchView(APIView):
    def post(self,request):
        # Until service authentication is configured, staff credentials are the only accepted internal identity.
        if not request.user.is_staff:return Response({"detail":"Staff service credentials are required."},status=403)
        entries=request.data.get("entries",[])
        if not isinstance(entries,list) or len(entries)>1000:return Response({"entries":["Provide a list of at most 1000 entries."]},status=400)
        created=[]
        for data in entries:
            org=get_object_or_404(Organization,pk=data.get("organization_id")); server=get_object_or_404(Servers,organization=org,pk=data.get("server_id")) if data.get("server_id") else None
            service=get_object_or_404(Service,server_id__organization=org,pk=data.get("service_id")) if data.get("service_id") else None
            metadata={str(k):("[REDACTED]" if any(secret in str(k).lower() for secret in ("password","token","secret","authorization")) else v) for k,v in dict(data.get("metadata",{})).items()}
            message=re.sub(r"(?i)(password|token|secret|authorization)\s*[:=]\s*\S+",r"\1=[REDACTED]",str(data.get("message","")))
            item=LogEntry.objects.create(organization=org,server_id=server,service_id=service,source=str(data.get("source",""))[:255],log_level=str(data.get("level","INFO"))[:32],message=message,metadata=metadata,logged_at=parse_datetime(data.get("logged_at","")) or timezone.now()); created.append(str(item.log_id))
        return Response({"created":created},status=201)
