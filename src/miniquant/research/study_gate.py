"""External data-support gate. Blocks a cohort, never deletes observations."""
def dispatch(mode,now_ms,end_ms,refresh,read_quality,invalidated,prepare,evaluate):
    if mode not in ('prepare','evaluate'):raise ValueError('Unknown study action')
    if mode=='evaluate' and now_ms<end_ms:
        return dict(status='not_due',real_outcomes_loaded=False,real_scores_computed=False)
    refresh()
    quality=read_quality()
    if invalidated() or quality.get('study_supported') is not True:
        return dict(status='study_blocked',real_scores_computed=False,action_dispatched=False)
    (prepare if mode=='prepare' else evaluate)()
    return dict(status='dispatched',mode=mode,action_dispatched=True)
