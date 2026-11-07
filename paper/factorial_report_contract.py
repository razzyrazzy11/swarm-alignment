"""Pure paper fields for amended reporting; no file, network or account access."""


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def interval_text(effect):
    _require(effect['n'] == 192, 'Effect source denominator must be 192')
    return (f"{100*effect['estimate']:+.2f} "
            f"[{100*effect['ci95'][0]:+.2f}, {100*effect['ci95'][1]:+.2f}] (95% CI)")


def bounds_text(bounds):
    _require(bounds['n'] == 192, 'Bound source denominator must be 192')
    return (f"[{100*bounds['estimate_lower']:+.2f}, "
            f"{100*bounds['estimate_upper']:+.2f}] (logical bounds)")


def sufficient_stats(record, procedure):
    views = record.get('by_view', record.get('observed_by_view'))
    return views['sufficient'][procedure]['raw']


def expected_fields(report):
    """Return exact manuscript tables with observed and planned units distinct."""
    a = report['analysis']; cfg = report['config']; models = cfg['monitors']
    _require(report['primary_complete'] is True and report['original_plan_complete'] is False,
             'Reporting requires complete primary and explicitly incomplete original plan')
    _require(a['sources'] == 192 and a['actor_calls'] == 576 and len(models) == 3,
             'Reporting source/actor/model grid differs')
    _require(a['original_audit_calls'] == 9742 and a['planned_original_audit_calls'] == 11640 and
             a['planned_extension_audit_calls'] == 4728, 'Reporting original/extension plan differs')
    _require(sum(a['models'][m]['availability']['unstarted'] for m in models) == 1898,
             'Reporting original missing calls differ')
    evidence = dict(status='primary complete; original secondary incomplete',
                    primary_complete=True, source_groups=a['sources'], actor_calls=a['actor_calls'],
                    original_audit_calls=a['original_audit_calls'],
                    extension_audit_calls=a['extension_audit_calls'],
                    main_audit_calls=a['main_audit_calls'], calibration_calls=a['calibration_calls'],
                    original_plan_complete=False, extension_plan_complete=report['extension_plan_complete'],
                    training_runs=0, freeze='factorial-audit-v1')
    labels = ('Adaption Gemma 26B', 'Adaption Gemma 31B', 'HF Novita')
    t1 = [['Original reader (planned sources)', 'Raw correct D / observed',
           'Raw correct P / observed', 'P minus D, percentage points']]
    for model, label in zip(models, labels):
        s = a['models'][model]
        direct = sufficient_stats(s, 'direct'); procedure = sufficient_stats(s, 'procedure')
        for metrics in (direct, procedure):
            _require(type(metrics['calls']) is int and 0 <= metrics['calls'] <= 192,
                     'Reader observed sufficient denominator differs')
        if model in a['complete_models']:
            _require(direct['calls'] == procedure['calls'] == 192, 'Complete reader sufficient grid differs')
            result = interval_text(s['primary_same_packet_procedure_minus_direct'])
        else:
            _require(model in a['partial_models'], 'Reader completion classification missing')
            result = bounds_text(s['sufficient_identification_bounds'])
        t1.append([label+' (192)', f"{direct['supported_definite']}/{direct['calls']}",
                   f"{procedure['supported_definite']}/{procedure['calls']}", result])
    t2 = [['Condition', 'Main observed / planned', 'Calibration observed / planned', 'Unstarted total']]
    records = [(label, a['models'][model]) for model, label in zip(models, labels)]
    conditions = a['extensions']['conditions']
    records += [(key, conditions[key]) for key in ('ds_off', 'ds_low', 'gemma_bridge')]
    for label, record in records:
        v = record['availability']
        _require(v['returned'] + v['unstarted'] == v['planned'] and
                 v['main_returned'] + v['calibration_returned'] == v['returned'],
                 'Reader availability counts differ')
        t2.append([label, f"{v['main_returned']}/{v['main_planned']}",
                   f"{v['calibration_returned']}/{v['calibration_planned']}", str(v['unstarted'])])
    t3 = [['Extension contrast on DIRECT sufficient', 'Status', 'Difference, percentage points']]
    contrasts = a['extensions']['contrasts']
    for key, label in (
        ('low_minus_off_direct_sufficient', 'ds_low minus ds_off (secondary)'),
        ('gemma_bridge_minus_adaption31_direct_sufficient', 'Gemma bundle minus Adaption31 (exploratory)')):
        item = contrasts[key]
        if item['status'] == 'complete':
            formatted = interval_text(item['result'])
        else:
            _require(item['status'] == 'partial', 'Extension contrast status differs')
            formatted = bounds_text(item['identification_bounds'])
        t3.append([label, item['status'], formatted])
    return dict(evidence_status=evidence, table2_model_ids=list(models), table1=t1, table2=t2, table3=t3)
