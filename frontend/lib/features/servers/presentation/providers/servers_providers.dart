import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/api/operational_api.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../organizations/domain/organization_context_state.dart';
import '../../../organizations/presentation/providers/organization_provider.dart';
import '../../domain/entities/server.dart';

final serversProvider=FutureProvider<List<Server>>((ref) async {
  final auth=ref.watch(authProvider); final org=ref.watch(organizationContextProvider);
  if(auth is! AuthAuthenticated||org is! OrganizationReady)return const[];
  final rows=await OperationalApi(auth.accessToken,org.activeMembership.organization.id).getResults('servers/',query:{'limit':'100'});
  return rows.map((raw){final x=raw as Map<String,dynamic>; final m=x['metrics'] as Map<String,dynamic>? ?? {};
    return Server(name:x['name']??'',environment:x['environment']??'',status:ServerStatus.values.firstWhere((s)=>s.name=='${x['status']}'.toLowerCase(),orElse:()=>ServerStatus.unknown),alertCount:x['alert_count']??0,cpu:metricPercent(m['cpu_r']).round(),memory:metricPercent(m['mem_u']).round(),disk:metricPercent(m['disk_u']).round(),lastSeen:relativeTime(x['last_seen_at']),uptime:'Unavailable',cpuHistory:(x['cpu_history'] as List? ??[]).map((v)=>(v as num).toDouble()/100).toList());}).toList();
});
