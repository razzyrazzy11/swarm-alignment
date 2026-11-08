"""Result-blind final-authoring handoff; never overwrites the paper or attests QA.

Diagnose checks sources, paths and commands without reading empirical reports.
Candidate delegates the existing strict complete-data gate and writes only a new
private authoring input. Scientific interpretation and every-page QA stay manual.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE_SHA='20bb4d221e722f7eca33c7bd3add4c749ddc76d346b12cdb9ada271083e3a36d'
STAGES=('hf_export','main_export','continuation_provenance','figure_input','figures','figure_provenance','generator_sensitivity')
SOURCE_FILES=('paper/complete-draft.json','paper/complete-reference-basis.json','paper/prepare_complete.py',
 'paper/complete_report_contract.py','paper/figure_build.py','paper/verify.py','paper/ledger_layout.py',
 'research/PAPER_COMPLETION_PLAN.md')
SLOTS=(
 ('primary','Verified G26 FULL16 P-minus-D estimate, interval and independent n; retain null/adverse effects.'),
 ('six_reader_tables','All six registered readers, every planned condition, delivery/validity/admission counts, matched effects and labeled denominators.'),
 ('actor_class_mix','Realized host actions and ground-truth label mix by assigned arm; compare always-NONE and ABSTAIN references.'),
 ('acquisition','Oracle answerability, supported correctness and restoration effects on matched trajectories; acquisition is distinct from evidence use.'),
 ('calibration','Separate scripted class-specific errors and coverage; do not pool with natural trajectories or claim population recall.'),
 ('influence','Controlled peer-note contrast with receiver state fixed; no emergent-collusion or covert-language inference.'),
 ('sensitivity','Registered generator-domain sensitivity and whether it changes the main conclusion; preserve the original primary.'),
 ('delivery','Retained serving failures and formatting failures over all requests; explicit denominators for conditional correctness.'),
 ('prior_iterations','Keep earlier all-NONE sample, completed original HF recovery and exploratory weight-policy work separate from MAIN.'),
 ('figures','Actual source-bound PNG hashes, captions and alt text; use verified figures, never layout-probe placeholders.'),
 ('interpretation','Which repair does each matched contrast support? Layers may coexist; sufficient evidence does not prove its internal use.'),
 ('limitations_ethics','Main-text decisive limitations plus required Limitations and Dual-Use / Ethical Considerations appendix.'),
 ('visual_review','Actual exported PDF, every page inspected by a reviewer, then hash-bound receipt; never infer inspection from a script.'),
 ('references_originality','Verify claim/source alignment and distinguish prior art, preexisting work and new sprint contribution.'))


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def private_target(output,root=ROOT):
    """Reject overwrite, alias/symlink, public/paper and sensitive destinations."""
    root=Path(root).resolve();raw=Path(output).absolute()
    require(raw.suffix=='.json' and raw.name not in ('.env','content.json'),'New private JSON filename required')
    require(not raw.name.lower().startswith(('.', 'id_rsa', 'id_ed25519', 'credentials', 'secret')),'Sensitive/hidden filename refused')
    require('..' not in raw.parts,'Relative-parent alias refused')
    allowed=root/'runs/paper-completion-handoff'
    for path in (raw,*raw.parents):
        require(not path.is_symlink(),'Output path alias/symlink refused')
    target=raw.resolve()
    require(target.is_relative_to(allowed) and target!=allowed,'Write only within private handoff directory')
    require(not target.exists(),'Never overwrite an existing authoring artifact')
    return target


def write_new(output,value,root=ROOT):
    target=private_target(output,root);target.parent.mkdir(parents=True,exist_ok=True)
    private_target(target,root)
    with target.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')
    return target


def committed_sources(root):
    result={}
    for name in SOURCE_FILES:
        path=Path(root)/name
        require(path.is_file() and not path.is_symlink(),'Required source missing or aliased: '+name)
        committed=subprocess.check_output(['git','show','HEAD:'+name],cwd=root)
        require(committed.replace(b'\r\n',b'\n')==path.read_bytes().replace(b'\r\n',b'\n'),'Commit/review source drift before handoff: '+name)
        result[name]=sha(path)
    return result


def pipeline(root):
    root=Path(root)
    require((root/'research/swarm-ledger-resume-v3-freeze.json').is_file(),'Provider-v3 registration required')
    efficient=(root/'research/swarm-ledger-efficient-v1-freeze.json').is_file()
    rate=(root/'research/swarm-ledger-rate-v1-freeze.json').is_file()
    paced=(root/'research/swarm-ledger-paced-v1-freeze.json').is_file()
    analysis_name='experiments.paced_resume_analysis' if paced else 'experiments.rate_resume_analysis' if rate else 'experiments.efficient_resume_analysis' if efficient else 'experiments.provider_resume_analysis'
    supervisor_name='experiments.paced_resume_supervisor' if paced else 'experiments.rate_resume_supervisor' if rate else 'experiments.efficient_resume_supervisor' if efficient else 'experiments.provider_resume_supervisor'
    waiter='runs/paced-resume-postprocess-driver' if paced else 'runs/rate-resume-postprocess-driver' if rate else 'runs/efficient-resume-postprocess-driver' if efficient else 'runs/provider-resume-postprocess-driver'
    collector='runs/swarm-ledger-paced-v1-driver' if paced else 'runs/swarm-ledger-rate-v1-driver' if rate else 'runs/swarm-ledger-efficient-v1-driver' if efficient else 'runs/swarm-ledger-resume-v3-driver'
    proof='research/swarm-ledger-paced-resume-release-proof.json' if paced else 'research/swarm-ledger-rate-resume-release-proof.json' if rate else 'research/swarm-ledger-efficient-resume-release-proof.json' if efficient else 'research/swarm-ledger-provider-resume-release-proof.json'
    analysis=importlib.import_module(analysis_name)
    supervisor=importlib.import_module(supervisor_name)
    prepare=importlib.import_module('paper.prepare_complete')
    analysis.verify()  # Frozen source/registration checks only, never aggregate admission.
    require(tuple(supervisor.STAGES)==STAGES==tuple(prepare.STAGES),'Offline stage/API drift')
    require('paper' in inspect.signature(prepare.candidate).parameters,'Candidate gate API differs')
    require('replay' in inspect.signature(analysis.verify_main).parameters,'Replay API differs')
    jobs=supervisor.processing_jobs();require(tuple(name for name,_ in jobs)==STAGES,'Offline command ordering differs')
    flat=[' '.join(command) for _,command in jobs]
    require(analysis_name+' export-hf' in flat[0],'HF admission command differs')
    require(analysis_name+' export-main' in flat[1],'MAIN admission command differs')
    require(waiter+'/verified-public-input.json' in flat[3],'Figure receipt path differs')
    state_path=root/(waiter+'/state.json')
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    return dict(analysis_module=analysis_name,
        collector_state=collector+'/state.json',
        postprocessor_state=waiter+'/state.json',
        observed_postprocessor_status=state.get('status','not_started'),
        observed_completed_stages=state.get('completed_stages',[]),
        stages=list(STAGES),commands=[dict(stage=name,argv=command) for name,command in jobs],
        strict_ready_required=True,
        complete_public='data/swarm-ledger-v1-public',
        main_proof=proof,
        figure_receipt=waiter+'/verified-public-input.json',
        figures='paper/figures/swarm-ledger-complete-v1',
        sensitivity='data/swarm-ledger-generator-sensitivity-v1')


def diagnose(root=ROOT):
    root=Path(root);paper=root/'paper';sources=committed_sources(root)
    template=paper/'official-template.docx'
    require(template.is_file() and sha(template)==TEMPLATE_SHA,'Official template drift')
    with zipfile.ZipFile(template) as archive:
        require(all(name in archive.namelist() for name in ('word/document.xml','word/styles.xml','word/fontTable.xml')),'Template layout/font parts missing')
    draft=json.loads((paper/'complete-draft.json').read_text(encoding='utf-8'))
    require(draft.get('preparation_status')=='RESULT-BLIND DRAFT \u2014 NOT FOR SUBMISSION','Committed result-blind draft required')
    require(draft.get('pending_results') and 'PENDING' in draft['abstract'],'Draft must not masquerade as completed findings')
    context=pipeline(root)
    for module in ('lxml.etree','pypdf','PIL.Image','pypdfium2','paper.complete_report_contract','paper.ledger_layout'):
        importlib.import_module(module)
    return dict(schema_version=1,created_at=datetime.now(timezone.utc).isoformat(),
        status='RESULT-BLIND HANDOFF \u2014 NOT A REPORT OR READINESS ATTESTATION',
        source_raw_sha256=sources,template_sha256=TEMPLATE_SHA,pipeline=context,
        author_slots=[dict(id=name,status='UNRESOLVED \u2014 fill only after complete strict replay',instruction=instruction) for name,instruction in SLOTS],
        authoring_steps=[
          dict(step=1,action='Wait for actual full collection and all seven offline stages, actual process termination and strict replay. Do not rerun stopped requests or stage commands blindly.'),
          dict(step=2,action='Create a new private verified-data candidate through the existing strict candidate gate.',command='python -m paper.completion_handoff candidate --output runs/paper-completion-handoff/<new-dated-candidate>.json'),
          dict(step=3,action='Read all verified findings and resolve the author slots, including null/adverse outcomes and decisive sensitivities. Add source-bound figures/captions/alt text. Candidate tables alone are insufficient.'),
          dict(step=4,action='Review the concrete manuscript; archive the historical content and outputs; then explicitly promote the reviewed candidate to paper/content.json. This tool never promotes it.'),
          dict(step=5,action='Build the reviewed official-template DOCX and export PDF with an owned hidden Word instance; preserve font/margins and maximum eight main pages excluding references/appendices.',command='python paper/figure_build.py'),
          dict(step=6,action='Render and actually inspect every PDF page. Only afterward create the truthful hash-bound figure-review receipt. Record the validated PDF manifest, then run both ordinary and optimized verification.',commands=['python paper/verify.py --record-pdf','python paper/verify.py','python -O paper/verify.py']),
          dict(step=7,action='Commit reviewed artifacts and require final CI. Then complete the four queued post-integration investigations/reviews in their preserved order. Submission is a separate user action.')],
        queued_reviews='Deferred until actual validation and paper integration; this handoff does not perform them.',
        scientific_validation_complete=False,paper_integration_complete=False,visual_qa_complete=False,
        empirical_reports_read=False,inference_calls=0,
        limits='Source/path/API/dependency diagnosis only. No outcome interpretation, visual review, publication, submission or completion guarantee.')


def create_candidate(output,root=ROOT):
    target=private_target(output,root)
    from paper import prepare_complete
    # Existing candidate calls ready() first: actual driver completion/death,
    # full scientific replay, HF reconstruction, figures and sensitivity gates.
    value=prepare_complete.candidate(Path(root)/'paper')
    return write_new(target,value,root)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('diagnose','candidate'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    private_target(args.output)
    target=write_new(args.output,diagnose()) if args.command=='diagnose' else create_candidate(args.output)
    print(json.dumps(dict(created=str(target),final_report=False,paper_promoted=False,visual_qa_complete=False,inference_calls=0)))

if __name__=='__main__':main()
