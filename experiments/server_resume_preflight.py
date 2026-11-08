"""Result-blind pipeline preflight; metadata only, no inference or scientific replay.

This companion is deliberately outside frozen collection sources. It detects
preventable environment/admission problems while collection is still running;
it cannot certify scientific validity, final pagination or visual inspection.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PHASES=('principal','coordinator','x','y','reporter','readers','calibration','influence')
BATCHES=('swarm-ledger-v1-main','swarm-ledger-resume-v1-main','swarm-ledger-resume-v2-main')
TARGETS=('data/swarm-ledger-v1-public','data/swarm-ledger-generator-sensitivity-v1',
 'research/hf-completed-original-results-v3.json','data/hf_completed_original_supplement_v3.jsonl',
 'research/swarm-ledger-server-resume-release-proof.json','paper/figures/swarm-ledger-complete-v1',
 'runs/server-resume-postprocess-driver/verified-public-input.json')
PLOT=Path('C:/Python314/python.exe')
TEMPLATE_SHA='20bb4d221e722f7eca33c7bd3add4c749ddc76d346b12cdb9ada271083e3a36d'
FONT_PARTS=('word/fonts/OldStandardTT-regular.ttf','word/fonts/OldStandardTT-bold.ttf',
            'word/fonts/OldStandardTT-italic.ttf')
DEPENDENCIES=('lxml.etree','pypdf','pypdfium2','PIL.Image',
 'experiments.server_resume_analysis','experiments.server_resume_supervisor',
 'analysis.ledger_complete_figures','analysis.ledger_generator_sensitivity',
 'paper.complete_report_contract','paper.prepare_complete')


def require(ok,message):
    if not ok:raise ValueError(message)


def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hex(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def complete_lines(path):
    """Ignore only an in-progress final line; malformed complete lines fail."""
    path=Path(path)
    if not path.exists():return [],False
    require(not path.is_symlink(),'Journal symlink refused')
    raw=path.read_bytes();partial=bool(raw and not raw.endswith(b'\n'))
    lines=raw.splitlines()
    if partial:lines=lines[:-1]
    return [json.loads(line) for line in lines],partial


def journal_metadata(root=ROOT):
    """Read operational fields only; do not inspect response text or native files."""
    root=Path(root);all_starts=set();all_terminal=set();plans={};counts={};partials=0
    batches=BATCHES+('swarm-ledger-resume-v3-main',) if (root/'research/swarm-ledger-resume-v3-freeze.json').exists() else BATCHES
    for phase in PHASES:
        for batch in batches:
            folder=root/'runs'/batch/phase
            # Responses first: a later start snapshot includes any concurrently
            # appended terminal's durable start, avoiding false subset alarms.
            terminals,tail_response=complete_lines(folder/'responses.jsonl')
            starts,tail_start=complete_lines(folder/'attempts.jsonl')
            partials+=int(tail_response)+int(tail_start)
            plan_path=folder/'plan.json'
            if not plan_path.exists():
                require(not terminals and not starts,'Unplanned journal rows')
                continue
            plan=json.loads(plan_path.read_text(encoding='utf-8'))
            require(_hex(plan.get('jobs_sha256')) and _hex(plan.get('freeze_sha256')),'Invalid plan commitment')
            ids=plan.get('ids');require(isinstance(ids,list) and len(set(ids))==len(ids),'Invalid plan identities')
            key=(plan['jobs_sha256'],tuple(ids))
            if phase in plans:require(plans[phase]==key,'Batch plan/body commitment differs')
            else:plans[phase]=key
            planned=set(ids);by_start={};by_terminal={}
            for row in starts:
                identity=row['id'];require(identity not in by_start and identity not in all_starts,'Duplicate/reissued start')
                require(identity in planned and _hex(row.get('request_sha256')),'Invalid started request commitment')
                amount=Decimal(row['reserved_cost']);require(amount.is_finite() and amount>=0,'Invalid reservation')
                by_start[identity]=row;all_starts.add(identity)
            for row in terminals:
                identity=row['id'];require(identity not in by_terminal and identity not in all_terminal,'Duplicate terminal')
                require(identity in by_start,'Terminal is not a started identity')
                require(row.get('profile_id')==by_start[identity].get('profile_id'),'Profile metadata changed')
                amount=Decimal(row['estimated_cost']);require(amount.is_finite() and amount>=0,'Invalid terminal cost')
                if row.get('known_usage') is False:
                    require(amount==Decimal(by_start[identity]['reserved_cost']),'Unknown usage lost full reservation')
                by_terminal[identity]=row;all_terminal.add(identity)
            if batch!=batches[-1]:require(set(by_start)==set(by_terminal),'Stopped prefix has unresolved start')
            counts[batch+'/'+phase]=dict(started=len(starts),terminal=len(terminals),in_flight=len(starts)-len(terminals))
    return dict(journals=counts,total_started=len(all_starts),total_terminal=len(all_terminal),
                partial_final_lines=partials,request_digest_scope='Digest syntax and unchanged full-plan commitment; exact-body/native replay remains final validation')


def process_snapshot(pid):
    """Actual process creation identity, without command lines or credentials."""
    require(type(pid) is int and pid>0,'Invalid process identity')
    if os.name!='nt':raise ValueError('Windows process-creation check required')
    command=f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue; if($p){{[pscustomobject]@{{pid=$p.Id;created_utc=$p.StartTime.ToUniversalTime().ToString('o')}}|ConvertTo-Json -Compress}}; exit 0"
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=15,check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def driver_metadata(root=ROOT):
    root=Path(root);result={}
    v3=(root/'research/swarm-ledger-resume-v3-freeze.json').exists()
    for name,expected in ((('swarm-ledger-resume-v3-driver' if v3 else 'swarm-ledger-resume-v2-driver'),('running','complete')),
                          ('hf-completion-v3-driver',('complete',)),
                          (('provider-resume-postprocess-driver' if v3 else 'server-resume-postprocess-driver'),('waiting_collection','processing','complete'))):
        path=root/'runs'/name/'state.json'
        if not path.exists():
            result[name]=dict(status='not_started',scientific_readiness=False);continue
        state=json.loads(path.read_text(encoding='utf-8'));require(state.get('status') in expected,'Owned driver stopped or invalid: '+name)
        updated=datetime.fromisoformat(state['updated'].replace('Z','+00:00'))
        require(updated.tzinfo is not None and updated<=datetime.now(timezone.utc),'Invalid driver timestamp')
        identities=[]
        for key in ('pid','child_pid'):
            if state.get(key) is None:continue
            observed=process_snapshot(state[key])
            created=datetime.fromisoformat(observed['created_utc'].replace('Z','+00:00')) if observed else None
            current=bool(created and created<=updated)
            if state['status'] in ('running','waiting_collection','processing') and key=='pid':
                require(current,'Owned active driver process absent/reused: '+name)
            if state['status']=='running' and key=='child_pid':require(current,'Owned active child absent/reused')
            identities.append(dict(role=key,pid=state[key],alive_with_expected_creation=current,created_utc=observed['created_utc'] if observed else None))
        result[name]=dict(status=state['status'],stage=state.get('stage'),processes=identities,
                         scientific_readiness=False,terminal_exit_pending=state['status']=='complete' and any(p['alive_with_expected_creation'] for p in identities))
    return result


def environment(root=ROOT,plot=PLOT):
    root=Path(root);plot=Path(plot);template=root/'paper/official-template.docx'
    require(template.is_file() and _sha(template)==TEMPLATE_SHA,'Official template changed/missing')
    with zipfile.ZipFile(template) as archive:
        require('word/fontTable.xml' in archive.namelist(),'Font table missing')
        fonts={name:hashlib.sha256(archive.read(name)).hexdigest() for name in FONT_PARTS}
        require(all(archive.getinfo(name).file_size>0 for name in FONT_PARTS),'Embedded font missing/empty')
    require(plot.is_file(),'Registered plotting Python missing')
    result=subprocess.run([str(plot),'-c','import json,matplotlib,PIL;print(json.dumps({"matplotlib":matplotlib.__version__,"PIL":PIL.__version__}))'],capture_output=True,text=True,timeout=30,check=True)
    versions=json.loads(result.stdout)
    for module in DEPENDENCIES:importlib.import_module(module)
    if (root/'research/swarm-ledger-resume-v3-freeze.json').exists():
        from experiments import provider_resume_analysis as release
        from experiments import provider_resume_supervisor as supervisor
    else:
        from experiments import server_resume_analysis as release
        from experiments import server_resume_supervisor as supervisor
    require(tuple(supervisor.STAGES)==('hf_export','main_export','continuation_provenance','figure_input','figures','figure_provenance','generator_sensitivity'),'Offline stage contract differs')
    for name in ('export_main','verify_main','export_hf','verify_hf','drivers','terminated'):
        require(callable(getattr(release,name,None)),'Offline function missing: '+name)
    require('replay' in inspect.signature(release.verify_main).parameters,'Scientific replay argument missing')
    targets={name:(root/name).exists() for name in (tuple(n.replace('swarm-ledger-server-resume-release-proof','swarm-ledger-provider-resume-release-proof') for n in TARGETS) if (root/'research/swarm-ledger-resume-v3-freeze.json').exists() else TARGETS)}
    require(not any(targets.values()),'Offline target already exists; never overwrite blindly')
    return dict(template_sha256=TEMPLATE_SHA,embedded_font_sha256=fonts,
                plot_dependencies=versions,imports_checked=len(DEPENDENCIES),new_output_targets=True,
                export_application_probe='Not performed; final Word export and actual-page QA remain required')


def check(root=ROOT):
    root=Path(root);issues=[];checks={}
    if (root/'research/swarm-ledger-resume-v3-freeze.json').exists():
        from experiments import swarm_ledger_resume_v3 as resume
        from experiments import provider_resume_analysis as analysis
    else:
        from experiments import swarm_ledger_resume_v2 as resume
        from experiments import server_resume_analysis as analysis
    for name,function in (
        ('collector_registration',lambda:dict(valid=bool(resume.verify()))),
        ('analysis_registration',lambda:dict(valid=bool(analysis.verify()))),
        ('contexts',lambda:context_metadata()),
        ('drivers',lambda:driver_metadata(root)),
        ('journals',lambda:journal_metadata(root)),
        ('environment',lambda:environment(root))):
        try:checks[name]=function()
        except Exception as error:issues.append(dict(check=name,error_class=type(error).__name__))
    return dict(schema_version=1,checked_at=datetime.now(timezone.utc).isoformat(),
        operational_preflight_passed=not issues,issues=issues,checks=checks,inference_calls=0,
        scientific_validation_complete=False,paper_integration_complete=False,visual_qa_complete=False,
        limits='Operational/environment preflight only; no outcome accuracy, native answer replay, complete scientific release, final PDF export, or actual-page inspection')


def context_metadata():
    from experiments import swarm_ledger_complete as s
    actual=s.digest(s.contexts('main'));registered=s.read(s.freeze_path('main'))['contexts_sha256']
    require(actual==registered,'Context commitment differs')
    return dict(valid=True,blocks=640,contexts_sha256=actual)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();value=check()
    if args.output:
        target=args.output.resolve();require(target.is_relative_to((ROOT/'runs').resolve()),'Write only under private runs')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value,indent=2));raise SystemExit(not value['operational_preflight_passed'])

if __name__=='__main__':main()
