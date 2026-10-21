"""Quota-aware research pacing; consumes a read-only app quota snapshot."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import math


def quota_decision(snapshot,now_ms,minimum_remaining=10,buffer_seconds=120):
    if not 0<minimum_remaining<100 or buffer_seconds<0:raise ValueError('Invalid quota policy')
    bucket=(snapshot.get('rateLimitsByLimitId') or {}).get('codex') or snapshot.get('rateLimits')
    if not isinstance(bucket,dict):return dict(action='hold_unknown',reason='quota_unavailable')
    windows={};low=[]
    for name in ('primary','secondary'):
        window=bucket.get(name)
        if not isinstance(window,dict):return dict(action='hold_unknown',reason='quota_window_unavailable')
        used=window.get('usedPercent');reset=window.get('resetsAt')
        if not isinstance(used,(int,float)) or isinstance(used,bool) or not math.isfinite(used):return dict(action='hold_unknown',reason='quota_percentage_unavailable')
        remaining=max(0,min(100,100-used))
        windows[name]=dict(remaining_percent=remaining,resets_at=reset)
        if remaining<minimum_remaining:low.append(name)
    allowed=snapshot.get('ordinaryUsageAllowed')
    if not low and allowed is True:return dict(action='continue',windows=windows)
    if not low:return dict(action='hold_unknown',reason='ordinary_usage_not_allowed_or_unknown',windows=windows)
    resets=[windows[name]['resets_at'] for name in low]
    if any(not isinstance(t,(int,float)) or isinstance(t,bool) or not math.isfinite(t) or t*1000<=now_ms for t in resets):return dict(action='hold_unknown',reason='reset_unavailable_or_already_past_requery_required',windows=windows)
    wake_seconds=math.ceil((max(resets)+buffer_seconds)/60)*60
    local=datetime.fromtimestamp(wake_seconds,ZoneInfo('Asia/Shanghai'))
    # Day/month constrained one-off heartbeat; after wake, recheck and restore15min.
    rule=f'FREQ=DAILY;BYMONTH={local.month};BYMONTHDAY={local.day};BYHOUR={local.hour};BYMINUTE={local.minute};BYSECOND=0;COUNT=1'
    return dict(action='wait_for_quota',windows=windows,blocking_windows=low,wake_at_utc=datetime.fromtimestamp(wake_seconds,timezone.utc).isoformat(),wake_at_shanghai=local.isoformat(),wake_at_epoch=wake_seconds,suggested_one_off_rrule=rule,requires_app_scheduler_update=True,note='Saved proposal is not a scheduled wake. Agent must call automation_update and verify success; wake must requery limits before resuming.')
