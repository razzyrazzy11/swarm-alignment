"""Result-blind preparation; verified complete public data is required to finalize.

Neither command overwrites content.json, the current report, or any experiment.
The candidate is an authoring input, never a visual-QA or submission attestation.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from paper import complete_report_contract as contract

PAPER = Path(__file__).resolve().parent
PLACEHOLDER = '[PENDING VERIFIED COMPLETE PUBLIC RELEASE — NOT A RESULT]'
STAGES = ('hf_export', 'main_export', 'continuation_provenance', 'figure_input',
          'figures', 'figure_provenance', 'generator_sensitivity')


def draft(paper=PAPER):
    """Use stable historical citation numbering and current author identity."""
    old = json.loads((Path(paper) / 'content.json').read_text(encoding='utf-8'))
    old = deepcopy(old)
    basis = json.loads((Path(paper) / 'complete-reference-basis.json').read_text(encoding='utf-8'))
    if (type(basis.get('schema_version')) is not int or basis['schema_version'] != 1
            or basis.get('source_release') != 'results-v3'
            or not isinstance(basis.get('references'), list)
            or len(basis['references']) != 31
            or any(not isinstance(text, str) or not text.startswith('['+str(i)+'] ')
                   for i, text in enumerate(basis['references'], 1))):
        raise ValueError('Historical reference basis requires review')
    old['references'] = deepcopy(basis['references'])
    additions = [
        'Kitaoka (2026). Open Problems in Securing Systems Against AI Agent Swarms. Swarm Alignment Hackathon, 5 November, recording 00:56:11-00:57:25. https://apartresearch.com/sprints/swarm-alignment-2026#schedule',
        'Kitaoka, Pham, Giudice and Merizian (2026). Red-Teaming Multi-Agent Attacks for Loss-of-Control Risks. MiniLab. https://arxiv.org/abs/2610.24052v1'
    ]
    talk_id = len(old['references']) + 1
    minilab_id = talk_id + 1
    old['references'].extend('['+str(talk_id+i)+'] '+text for i,text in enumerate(additions))
    value = {k: deepcopy(old[k]) for k in ('author', 'affiliation', 'references')}
    value.update(title='When Can a Swarm Be Audited?',
        subtitle='Track 4: Multi-Agent Oversight and Control',
        preparation_status='RESULT-BLIND DRAFT — NOT FOR SUBMISSION',
        abstract=PLACEHOLDER,
        sections=[
          ['1. Introduction', [
            'A worker reports that a delegated update was completed. An investigator must establish who acted and whether the authority still held. A missing authentic record and a mistaken interpretation of an available record call for different interventions. We ask: does a swarm auditor lack necessary evidence, or fail to use evidence that is already sufficient?',
            'This Track 4 study separates three stages: obtaining trustworthy evidence, delivering a usable verdict, and reasoning from evidence sufficient in a declared finite history model. The setting is bounded fake-data delegation; it does not expose real services to agent actions. Multi-agent risk motivates oversight [1,9,10]; the target here is a specific worker-event label, not intent or causal blame for the entire group [6].']],
          ['2. Related work and contribution', [
            'Evidence-binding work distinguishes correct answers from justified findings [3]. Active evidence acquisition changes what an investigator observes [24]; selective prediction distinguishes justified abstention from an unsupported definite answer [25]. We use these distinctions as separate evaluation layers rather than treating a better information packet as proof of improved reasoning.',
            'Prior Apart projects such as Syscon and ActionLens connect instrumentation to a testable oversight decision [11,12]. Our contribution is a prospectively registered matched comparison within a stateful, five-role workflow: instruction changes keep evidence fixed, while restoration comparisons keep source trajectories matched. The bounded scope and baselines limit claims of transfer.']],
          ['3. Methods', [
            'A principal issues authority, a coordinator delegates it, workers X and Y hand off work and propose bounded fake writes, and a reporter produces untrusted claims. The host executes parsed bounded fake-data actions; authorization violations are measured rather than silently prevented. Y permission depends jointly on issuance and grant, local cap, shared budget, half-open lease, and revocation. Physical X usage counts toward the shared budget even when X lacked authority. API latency does not advance the fake integer settlement clock.',
            'The registered grid has four actor profiles, five policy classes, two layouts and sixteen repetitions. The same principal/coordinator prefix is cloned across honest, X-adversarial, Y-adversarial and both-adversarial arms. Repeated arms, views and readers are dependent measurements, not additional independent samples.',
            'All six FULL16 readers receive DIRECT and PROCEDURE instructions on the same four-arm evidence: Adaption Gemma 26B and 31B; Hugging Face Llama text and schema delivery; and Ollama DeepSeek thinking off and low [16,17,31]. These are six profiles, four checkpoints and three model families. G26, G31 and DS-low also read six reduced/restored views under DIRECT on the matched honest/both arms, covering two families.',
            'Acquisition conditions distinguish a sufficient seven-record receipt packet, random loss, selective loss, and restoration of two authentic records selected randomly, by metadata, or by a fixed contract bundle. Query selection uses a declared uniform compatible-world prior, not the empirical incident distribution. Peer claims never create authority.',
            'The primary is G26 FULL16 PROCEDURE minus DIRECT in parsed ungated correct-definite verdicts. First average four arm differences within each base block, then average 640 blocks. The frozen stratified block bootstrap uses forty strata, sixteen blocks each, 10,000 draws and seed 730009. Secondary intervals are descriptive, without familywise claims. Semantic validity, strict bare-JSON encoding, admitted output, wrong sufficient-evidence verdicts, and supported abstention remain distinct.',
            'Always-NONE, always-ABSTAIN and the finite-domain support oracle are references. Calibration uses twenty scripted worlds, separately from natural trajectories. Controlled inter-agent influence holds the receiver state fixed and varies three peer notes across eighty blocks. Small-monitor fine-tuning is not performed. Failed requests remain terminal and in denominators; no request identity is retried or replaced.']],
          ['4. Results', [PLACEHOLDER, 'TABLE1', 'TABLE2', 'TABLE3']],
          ['5. Interpretation and implications', [
            'Interpret acquisition gains alongside changes in oracle answerability and supported correctness. Interpret a procedure gain on sufficient evidence as an operational instruction effect, not a demonstration of an internal cognitive mechanism. A format or serving failure is failed verdict delivery; an admitted parsed wrong verdict with sufficient evidence is a different failure.',
            'The six-reader grid tests how robust these distinctions are across the registered implementations. The schema/text and thinking-mode contrasts are matched interventions, whereas comparisons between different hosted checkpoints can bundle weights, quantization, templates and serving differences. Empirical conclusions must follow the complete results and uncertainty, including null or adverse effects.']],
          ['6. Conclusion', [
            'The practical oversight decision is whether to recover an authentic witness, change how a reader uses an already sufficient packet, or repair verdict delivery. This instrument measures those possibilities separately in a bounded workflow. General swarm safety and hidden intent require further evidence.']]],
        appendix=[
          ['Appendix A. Limitations and Dual-Use / Ethical Considerations', [
            'The environment is synthetic and finite; its role graph, policies, receipt trust assumptions, and model routes limit external validity. The target is Y event authorization/execution, not all group behavior or causal responsibility. Repeated calls do not increase the independent block count. Hosted model identities can drift; route/model checks do not establish immutable weights.',
            'Oracle answerability is relative to its declared compatible-world domain. The five-policy generator can encode correlations that a generator-aware reader could exploit. The separately registered generator-knowledge sensitivity must be discussed with the primary domain; it does not replace or rescore the original primary. The uniform acquisition prior is not an empirical posterior.',
            'Only bounded fake-data actions are executed. No live target, credential theft, real exfiltration, or real-world sabotage is required. Public artifacts should omit credentials, private provider response identifiers and unnecessary raw text. Failure modes could help evasion or selective deletion; release emphasizes defensive evidence requirements and safe reproductions. No claim of perfect containment or tamper-proof deployment follows.']],
          ['Appendix B. Provenance, iterations and reproducibility', [
            'The earlier October trusted-agent-sting project [19] is preexisting context, not new sprint evidence. Earlier swarm-audit, weight-policy and incomplete-serving iterations are separately registered and retained; they are not pooled into the new 640-block primary. The original HF completion is a separate recovery of its original planned identities, not a replacement reader in this MAIN.',
            'Router-aware continuation preserves stopped-prefix hashes and collects only unstarted identities. Authentic connection and gateway failures remain terminal, retain unknown-cost reservations where needed, and are not reasoning outcomes. Scheduling amendments and excluded capacity/serving pilots are separately labeled. The post-primary serving pilot is feasibility evidence only, not an extra scientific condition.',
            'AI tools assisted implementation and writing; the author is responsible for claims, references and data. Completion requires strict offline public replay, source and registration checks, figure provenance, and actual inspection of every exported PDF page. A successful metadata health check does not establish scientific correctness.']]],
        pending_results=PLACEHOLDER)
    # New talk context is editorial, after registration and before MAIN accuracy
    # inspection. It changes neither estimands nor which outcomes are reported.
    value['sections'][0][1].append(
        'The practical decision is whether an investigator should recover a missing authentic record, repair verdict delivery, or change how an auditor reads an already sufficient packet. Measuring these separately can prevent spending a monitor-improvement budget on the wrong failure.')
    value['sections'][1][1].append(
        'Kitaoka explicitly separates identifying the relevant agents and evidence from residual monitor failures with combined evidence ['+str(talk_id)+']. MiniLab studies distributed attacks that evade isolated-trajectory monitors ['+str(minilab_id)+']. Our contribution is the prospectively registered matched instrument for stateful delegation, not the invention of that distinction or a replication of MiniLab.')
    value['sections'][2][1].append(
        'Host-produced action records are assumed authentic; worker and reporter statements are untrusted. Hash-bound archives detect changes to retained files, not whether a compromised host told the truth. The fixed five-role team tests a controlled component of swarm oversight; it does not demonstrate spontaneous organization or containment of an arbitrary autonomous swarm.')
    value['sections'][4][1].append(
        'Read acquisition effects beside oracle answerability, then output validity, then supported and correct verdicts. More answerable packets do not by themselves establish better reasoning; a procedure effect with identical sufficient evidence does not establish that an internal mechanism changed. Assigned adversarial instructions are not successful attacks: report realized host actions and class composition separately, including null effects and failures.')
    value['sections'][4][1].append(
        'These are diagnostic layers, not mutually exclusive causes. A missing record can coexist with a delivery failure. Report delivery and instruction-assignment outcomes over all planned requests, and label sufficient-evidence and admitted-output subsets with their own denominators. A correct but unsupported guess is not a supported finding; justified abstention can be appropriate when evidence is insufficient. The frozen primary remains unchanged, and any new cross-layer breakdown is descriptive.')
    value['appendix'][1][1].append(
        'The earlier 192-source natural sample contained only NONE labels, so its procedure gains concern reduced false accusations and cannot establish incident recall. The new study must report its actual label mix and separate scripted calibration; no attack success is inferred from its assigned arm. Controlled peer-note influence is not evidence of an emergent covert language. Talk context was reviewed after registration with MAIN accuracy still blinded; it does not create new confirmatory outcomes or authorize fine-tuning on the test set.')
    # Retain only sources actually used in this new paper and renumber them.
    text = ' '.join(p for _, ps in value['sections'] + value['appendix'] for p in ps)
    pattern = r'\[(\d+(?:,\d+)*)\]'
    used = sorted({int(n) for group in re.findall(pattern, text) for n in group.split(',')})
    mapping = {old: new for new, old in enumerate(used, 1)}
    rewrite = lambda text: re.sub(pattern, lambda m: '[' + ','.join(str(mapping[int(n)]) for n in m[1].split(',')) + ']', text)
    value['references'] = [rewrite(old['references'][n - 1]) for n in used]
    for kind in ('sections', 'appendix'):
        value[kind] = [[heading, [rewrite(p) for p in paragraphs]] for heading, paragraphs in value[kind]]
    return value


def ready(paper=PAPER):
    """Gate before reading any complete empirical aggregate."""
    paper = Path(paper)
    v2=(paper.parent/'research/swarm-ledger-resume-v2-freeze.json').is_file()
    v3=(paper.parent/'research/swarm-ledger-resume-v3-freeze.json').is_file()
    efficient=(paper.parent/'research/swarm-ledger-efficient-v1-freeze.json').is_file()
    rate=(paper.parent/'research/swarm-ledger-rate-v1-freeze.json').is_file()
    waiter='rate-resume-postprocess-driver' if rate else 'efficient-resume-postprocess-driver' if efficient else 'provider-resume-postprocess-driver' if v3 else 'server-resume-postprocess-driver' if v2 else 'router-resume-postprocess-driver'
    state_path = paper.parent / ('runs/'+waiter+'/state.json')
    if not state_path.is_file():
        raise ValueError('Actual complete postprocessor state required')
    state = json.loads(state_path.read_text(encoding='utf-8'))
    if state.get('status') != 'complete' or state.get('completed_stages') != list(STAGES) or state.get('child_pid') is not None:
        raise ValueError('All actual offline postprocessing stages must finish first')
    if rate:
        from experiments import rate_resume_analysis as continuation
    elif efficient:
        from experiments import efficient_resume_analysis as continuation
    elif v3:
        from experiments import provider_resume_analysis as continuation
    elif v2:
        from experiments import server_resume_analysis as continuation
    else:
        from experiments import router_resume_analysis as continuation
    continuation.terminated('runs/'+waiter+'/state.json', complete=True)
    continuation.drivers('main')
    continuation.drivers('hf')
    report, bindings = contract.load_completed(paper, replay=True)
    continuation.verify_hf()
    from analysis import ledger_complete_figures as figures
    figures.verify_only(paper.parent / 'data/swarm-ledger-v1-public',
                        paper.parent / ('runs/'+waiter+'/verified-public-input.json'),
                        paper / 'figures/swarm-ledger-complete-v1')
    bindings['generator_sensitivity_report_sha256'] = verify_sensitivity(paper)
    return report, bindings


def verify_sensitivity(paper=PAPER):
    """Replay the frozen secondary calculation; never accept existence alone.

    The caller first verifies the complete MAIN public release. This companion
    reuses the frozen sensitivity implementation instead of changing its source.
    """
    from analysis import ledger_generator_sensitivity as sensitivity
    root = Path(paper).parent
    source = root / 'data/swarm-ledger-v1-public'
    target = root / 'data/swarm-ledger-generator-sensitivity-v1'
    inventory = sensitivity.raw_inventory(source)
    registration = sensitivity.verify()
    actual_files = sensitivity.raw_inventory(target)
    expected_names = {'report.json', 'packets.jsonl', 'verdicts.jsonl', 'registration.json'}
    if set(actual_files) != expected_names:
        raise ValueError('Sensitivity export inventory differs')
    report_path = target / 'report.json'
    value = json.loads(report_path.read_text(encoding='utf-8'))
    artifacts, original_report, manifest = sensitivity.analysis.load_public_artifacts(source)
    scientific, packets, verdicts = sensitivity.summarize(artifacts)
    extra = {'created', 'registration_sha256', 'input_files_raw_sha256',
             'input_manifest_raw_sha256', 'input_report_raw_sha256', 'input_verification',
             'original_primary_unchanged', 'original_primary_commitment', 'provenance_limit',
             'derived_files_raw_sha256'}
    if (set(value) != set(scientific) | extra
            or sensitivity.study.canonical({k: value[k] for k in scientific}) != sensitivity.study.canonical(scientific)):
        raise ValueError('Sensitivity scientific reconstruction differs')
    stamp = datetime.fromisoformat(value['created'])
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError('Sensitivity export timestamp invalid')
    if (value['registration_sha256'] != sensitivity.study.sha(sensitivity.REGISTRATION)
            or sensitivity.study.canonical(json.loads((target / 'registration.json').read_text(encoding='utf-8')))
            != sensitivity.study.canonical(registration)):
        raise ValueError('Sensitivity registration differs')
    if (value['input_files_raw_sha256'] != inventory
            or value['input_manifest_raw_sha256'] != inventory['manifest.json']
            or value['input_report_raw_sha256'] != inventory['report.json']):
        raise ValueError('Sensitivity input commitment is stale')
    if (value['original_primary_unchanged'] is not True
            or value['original_primary_commitment'] != sensitivity.study.digest(original_report['primary'])
            or value['provenance_limit'] != manifest['provenance_limit']
            or not isinstance(value['input_verification'], dict)
            or value['input_verification'].get('valid') is not True):
        raise ValueError('Sensitivity primary/provenance commitment differs')
    derived = {name: actual_files[name] for name in ('packets.jsonl', 'verdicts.jsonl', 'registration.json')}
    if value['derived_files_raw_sha256'] != derived:
        raise ValueError('Sensitivity derived-file commitment differs')
    for name, expected in (('packets.jsonl', packets), ('verdicts.jsonl', verdicts)):
        actual = (target / name).read_text(encoding='utf-8')
        wanted = ''.join(sensitivity.study.canonical(row) + '\n' for row in expected)
        if actual != wanted:
            raise ValueError('Sensitivity derived rows differ: ' + name)
    if sensitivity.raw_inventory(source) != inventory or sensitivity.raw_inventory(target) != actual_files:
        raise ValueError('Sensitivity artifacts changed during replay')
    return actual_files['report.json']


def candidate(paper=PAPER):
    report, bindings = ready(paper)
    value = draft(paper)
    value.pop('pending_results')
    value['preparation_status'] = 'VERIFIED-DATA CANDIDATE — AUTHOR INTERPRETATION AND VISUAL REVIEW REQUIRED'
    value['ledger_registration'] = contract.REGISTRATION
    value.update(contract.expected_fields(report))
    anchors = contract.expected_anchors(report)
    for heading, paragraphs in value['sections']:
        if heading == '3. Methods':
            paragraphs.extend([anchors['workload'], anchors['acquisition'], anchors['oracle_scope']])
        if heading == '4. Results':
            paragraphs[0] = anchors['primary']
    value['abstract'] = (
        'Does a swarm auditor lack necessary evidence, or fail to use evidence that is already sufficient? '
        'This Track 4 study separates acquisition, verdict delivery and reasoning in a bounded fake-data delegation workflow. '
        'A principal and coordinator authorize two workers; workers hand off tasks and propose host-bounded actions; a reporter supplies untrusted claims. '
        'The registered MAIN uses 640 independent blocks and 2,560 assigned trajectories. '
        'Adaption, Hugging Face and Ollama supply six reader profiles across three families, producing 53,760 main readings and 240 separate scripted calibration readings. '
        + anchors['primary'] + ' '
        'Matched restoration comparisons change the available authentic records; instruction comparisons keep sufficient evidence fixed. '
        'Always-NONE, always-ABSTAIN and a finite-domain support oracle bound interpretation. '
        'Serving, formatting and reasoning failures remain separately reported, with no repeated request identities. '
        'Oracle sufficiency depends on the declared compatible-history domain, and the uniform acquisition prior is not the generator posterior. '
        'A separate generator-knowledge sensitivity qualifies transfer. These findings concern a finite workflow and registered implementations, not universal swarm safety or hidden intent.')
    value['table1_caption'] = 'Table 1. FULL16 correct-definite verdicts and matched procedure effects. Each procedure uses 2,560 trajectories; intervals resample 640 independent blocks. Secondary intervals are descriptive.'
    value['table2_caption'] = 'Table 2. Complete reader workloads, admitted output, semantic validity and strict JSON compliance. Repeated readings do not increase independent n.'
    value['table3_caption'] = 'Table 3. Contract restoration versus selective loss on 1,280 matched honest/both trajectories within 640 blocks per acquisition reader.'
    value['preparation_bindings'] = bindings
    contract.validate_manuscript(value, report)
    if not 150 <= len(value['abstract'].split()) <= 250:
        raise ValueError('Candidate abstract length requires author revision')
    return value


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('draft', 'candidate'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {(PAPER / 'content.json').resolve()} or args.output.resolve().is_relative_to((PAPER / 'out').resolve()):
        raise ValueError('Preparation cannot replace the current manuscript or report')
    write_new(args.output, draft() if args.command == 'draft' else candidate())
    print(json.dumps(dict(created=str(args.output), final_report=False, visual_qa_complete=False, inference_calls=0)))


if __name__ == '__main__':
    main()
