"""Offline manuscript contract for the completed, separately registered six-reader MAIN.

Pure expected_* helpers accept a verified aggregate report. File validation uses
its frozen public replay; no private journals, keys, providers or training.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

REGISTRATION='swarm-ledger-complete-v1-main'
READERS=('g26','g31','hf_text','hf_schema','ds_off','ds_low')
AUXILIARY=('g26','g31','ds_low')
VIEWS=('receipt_only7','random_loss','selective_loss','selective_random2','selective_metadata2','selective_contract2')
LABELS={'g26':'Adaption Gemma 26B','g31':'Adaption Gemma 31B','hf_text':'HF Llama, text',
        'hf_schema':'HF Llama, schema','ds_off':'Ollama DeepSeek, off','ds_low':'Ollama DeepSeek, low'}


def require(ok,message):
    if not ok:raise ValueError(message)


def effect_text(effect):
    require(effect['blocks']==640 and effect['strata']==40,'Effect independent-block denominator differs')
    values=[effect[k] for k in ('estimate','lower','upper')]
    require(all(type(v) in (int,float) and math.isfinite(v) and -1<=v<=1 for v in values)
            and effect['lower']<=effect['upper'],'Invalid aggregate effect/interval')
    return f"{100*effect['estimate']:+.2f} [{100*effect['lower']:+.2f}, {100*effect['upper']:+.2f}]"


def validate_report(report):
    require(report['study_id']=='swarm-ledger-v1' and report['registration_prefix']=='swarm-ledger-complete-v1',
            'Separate completed-study registration required')
    require(report['main_reader_profiles']==list(READERS) and report['auxiliary_reader_profiles']==list(AUXILIARY),
            'Six-reader/three-acquisition profile grid differs')
    require(report['source_blocks']==640 and report['assigned_trajectories']==2560 and report['reader_responses']==53760,
            'Completed MAIN source/reader denominator differs')
    require(report['calibration']['responses']==240,'Calibration denominator differs')
    require(report['primary']['draws']==10000,'Registered bootstrap draw count differs')
    effect_text(report['primary'])
    for phase,n in dict(principal=640,coordinator=640,x=2560,y=2560,reporter=2560,readers=53760,calibration=240,influence=240).items():
        c=report['coverage'][phase]
        require(c['complete'] is True and c['planned']==c['started']==c['terminal']==n and c['unstarted']==0,
                'Incomplete actual MAIN phase: '+phase)
    require(all(c['complete'] is True and c['unstarted']==0 for c in report['coverage'].values()),'Engineering or main graph incomplete')
    expected={p+':full:'+method:2560 for p in READERS for method in ('direct','procedure')}
    expected.update({p+':'+v+':direct':1280 for p in AUXILIARY for v in VIEWS})
    require(set(report['conditions'])==set(expected),'Complete condition grid differs')
    for key,n in expected.items():
        m=report['conditions'][key]
        require(m['responses']==n and m['independent_blocks']==640 and m['actual_positive']+m['actual_negative']==n,
                'Profile/view denominator differs: '+key)
        require(all(type(v) is int and 0<=v<=n for v in m['numerators'].values()),'Invalid condition numerator')
    require(sum(m['responses'] for m in report['conditions'].values())==53760,'Reader response sum differs')
    require(set(report['secondary_procedure_effects'])==set(READERS)-{'g26'},'Secondary reader grid differs')
    for effect in report['secondary_procedure_effects'].values():effect_text(effect)
    # Every displayed acquisition contrast is matched over the same640 blocks,
    # using two arms (1280 trajectories), never a new independent sample.
    contrasts=[v+'-selective_loss' for v in ('receipt_only7','random_loss','selective_random2','selective_metadata2','selective_contract2')]
    contrasts+=['selective_metadata2-selective_random2','selective_contract2-selective_metadata2']
    require(set(report['acquisition_direct'])=={p+':'+v for p in AUXILIARY for v in contrasts},'Acquisition contrast grid differs')
    for effects in report['acquisition_direct'].values():
        require(set(effects)=={'correct_supported_including_required_abstention','correct_definite','oracle_answerability'},'Acquisition metric grid differs')
        for effect in effects.values():effect_text(effect)
    return report


def expected_anchors(report):
    validate_report(report)
    return {
      'workload':'The new MAIN contains 640 independent base blocks and 2,560 assigned trajectories, with 53,760 main reader responses, 240 separate scripted calibration responses, and 9,200 actor calls including the exploratory influence receivers.',
      'primary':'The primary G26 FULL16 procedure-minus-direct effect in parsed ungated correct definite verdicts is '+effect_text(report['primary'])+' percentage points (95% stratified bootstrap confidence interval; 640 independent base blocks).',
      'acquisition':'Acquisition comparisons use the honest and both arms only: 1,280 matched trajectories in the same 640 base blocks per reader and view. Six reader profiles span three model families; the three acquisition profiles span two families.',
      'oracle_scope':"Oracle answerability is relative to the declared finite-policy compatible-world domain. Its uniform acquisition prior is not the cohort sampling posterior. A reader with knowledge of the five-policy generator could exploit budget-time/revocation correlations beyond the stated oracle history model."}


def expected_fields(report):
    validate_report(report)
    t1=[['FULL16 reader','Correct definite D / P (each /2560)','P minus D, pp [95% CI]']]
    t2=[['Reader','Main responses','Admitted / semantic valid / strict JSON']]
    for p in READERS:
        d=report['conditions'][p+':full:direct'];q=report['conditions'][p+':full:procedure']
        effect=report['primary'] if p=='g26' else report['secondary_procedure_effects'][p]
        t1.append([LABELS[p],f"{d['numerators']['correct_definite']} / {q['numerators']['correct_definite']}",effect_text(effect)])
        rows=[m for k,m in report['conditions'].items() if k.startswith(p+':')]
        t2.append([LABELS[p],str(sum(m['responses'] for m in rows)),
          ' / '.join(str(sum(m['numerators'][key] for m in rows)) for key in ('admitted','semantic_valid','strict_json'))])
    t3=[['Contract restoration minus selective loss','Oracle answerability, pp','Correct definite, pp','Correct supported, pp']]
    for p in AUXILIARY:
        e=report['acquisition_direct'][p+':selective_contract2-selective_loss']
        t3.append([LABELS[p],effect_text(e['oracle_answerability']),effect_text(e['correct_definite']),effect_text(e['correct_supported_including_required_abstention'])])
    return dict(table2_source='swarm_ledger_complete',table2_model_ids=list(READERS),table1=t1,table2=t2,table3=t3,
      evidence_status=dict(status='completed prospectively registered six-reader MAIN',freeze=REGISTRATION,
        source_blocks=640,assigned_trajectories=2560,main_reader_responses=53760,calibration_responses=240,
        actor_calls_including_influence=9200,training_runs=0),
      ledger_results=dict(conditions={k:dict(responses=v['responses'],independent_blocks=v['independent_blocks'],
          actual_positive=v['actual_positive'],actual_negative=v['actual_negative'],numerators=deepcopy(v['numerators']))
          for k,v in report['conditions'].items()},primary=deepcopy(report['primary']),
          acquisition_direct=deepcopy(report['acquisition_direct'])))


def validate_manuscript(content,report):
    require(content.get('ledger_registration')==REGISTRATION,'Unknown ledger manuscript registration')
    for key,value in expected_fields(report).items():
        require(content.get(key)==value,'Completed manuscript aggregate differs: '+key)
    text=' '.join([content['abstract']]+[p for _,ps in content['sections']+content['appendix'] for p in ps]
                  +[v['caption'] for v in content.get('figures',[])])
    compact=lambda v:' '.join(v.split())
    for key,sentence in expected_anchors(report).items():
        require(compact(sentence) in compact(text),'Missing/stale scientific manuscript anchor: '+key)
    first=content['abstract']+' '+content['title']+' '+' '.join(content['sections'][0][1])
    require('Track 4' in first,'Track 4 must be explicit on first page')
    require(re.search(r'fake[ -]data',text,re.I) is not None,'Bounded fake-data scope missing')
    require(any('Limitations and Dual-Use / Ethical Considerations' in h for h,_ in content['appendix']),
            'Required limitations/dual-use appendix missing')
    require(all(name in content['abstract'] for name in ('Adaption','Hugging Face','Ollama')),'Service evidence missing from abstract')
    return True


def load_completed(root,replay=True):
    """Read future completed PUBLIC release only, behind explicit manuscript flag.

    Full frozen replay validates scientific arithmetic, completeness and native
    commitments. It never uses private collection files or exposes raw text.
    """
    import sys
    repository=str(Path(__file__).resolve().parents[1])
    if repository not in sys.path:sys.path.insert(0,repository)
    from experiments import swarm_ledger_complete_analysis as analysis
    directory=Path(root).parent/'data/swarm-ledger-v1-public'
    require(directory.is_dir(),'Completed public release required; planned/toy report is insufficient')
    if replay:analysis.verify_public(directory)
    if (Path(root).parent/'research/swarm-ledger-resume-v2-freeze.json').exists():
        from experiments import server_resume_analysis as continuation
        continuation.verify_main(directory,replay=False)
    elif (Path(root).parent/'research/swarm-ledger-resume-v1-freeze.json').exists():
        from experiments import router_resume_analysis as continuation
        continuation.verify_main(directory,replay=False)
    _,report,manifest=analysis.load_public_artifacts(directory)
    validate_report(report)
    bindings={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
              for name in ('manifest.json','report.json','registration.json','operational-registration.json')}
    bindings.update(scientific_registration_sha256=manifest['registration_sha256'],
                    operational_registration_sha256=manifest['operational_registration_sha256'])
    for name in ('server-resume-analysis-v1-freeze.json','swarm-ledger-resume-v2-freeze.json',
                 'swarm-ledger-server-resume-release-proof.json',
                 'router-resume-analysis-v1-freeze.json','swarm-ledger-resume-v1-freeze.json',
                 'swarm-ledger-resume-release-proof.json','hf-completion-v3-freeze.json',
                 'hf-completed-original-results-v3.json','adaption-serving-pilot-v1-freeze.json',
                 'adaption-serving-pilot-results.json'):
        path=Path(root).parent/'research'/name
        if path.exists():bindings[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return report,bindings
