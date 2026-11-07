"""Scientific figures from a verified, complete public swarm-ledger export.

Run verify-input with the PRIMARY scientific Python; generate uses the existing
Matplotlib interpreter. verify-only checks provenance hashes without replaying
statistics. No monitor calls, credentials or private run journals are accessed.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PROFILES=('g26','g31','q397','glm52','hf_text','hf_schema','ds_off','ds_low')
NAMES={'g26':'Gemma 26B','g31':'Gemma 31B','q397':'Qwen 397B','glm52':'GLM 5.2',
       'hf_text':'Llama Scout: text','hf_schema':'Llama Scout: schema','ds_off':'DeepSeek: off','ds_low':'DeepSeek: low'}
VIEWS=('full','receipt_only7','random_loss','selective_loss','selective_random2','selective_metadata2','selective_contract2')
VIEW_NAMES=('Full evidence (16)','Receipt-only (7)','Random loss (−4)','Selective loss (−4)',
            'Random restore (+2)','Metadata restore (+2)','Contract restore (+2)')
ARMS={'honest','x_adversarial','y_adversarial','both'}
PROVENANCE='ledger_figures_provenance.json'


def expect(ok,message):
    if not ok:raise ValueError(message)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    def pairs(items):
        value={}
        for k,v in items:expect(k not in value,'Duplicate JSON key');value[k]=v
        return value
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def input_hashes(directory):
    directory=Path(directory);expect(directory.is_dir() and not directory.is_symlink(),'Public directory invalid')
    files=list(directory.iterdir());expect(all(p.is_file() and not p.is_symlink() for p in files),'Public inputs must be regular files')
    return {p.name:digest(p) for p in sorted(files)}


def source_hashes(directory=None):
    # Byte hashing is provenance checking, not a second statistical implementation.
    names={'experiments/swarm_ledger.py','experiments/swarm_ledger_reference.py',
           'experiments/swarm_ledger_study.py','experiments/swarm_ledger_analysis.py'}
    if directory is not None:
        registered=read(Path(directory)/'registration.json')['source_sha256']
        for name in registered:
            path=Path(name)
            expect(not path.is_absolute() and not path.drive and '..' not in path.parts and '\\' not in name and
                   path.parts[0] in ('experiments','research','data') and not any(p.startswith('.') for p in path.parts),
                   'Registered public source path invalid')
            names.add(name)
    return {name:digest(ROOT/name) for name in sorted(names)}


def verify_input(directory,receipt,verification_python=None):
    """Perform the full frozen replay exactly once with the specified Python."""
    directory=Path(directory).resolve();receipt=Path(receipt)
    expect(not receipt.exists(),'Verification receipt exists; use a new receipt path')
    before=input_hashes(directory);sources=source_hashes(directory)
    verification_python=Path(verification_python) if verification_python is not None else Path(sys.executable)
    script=('import json,platform,sys;from experiments import swarm_ledger_analysis as a;'
            'v=a.verify_public(sys.argv[1]);'
            'print(json.dumps(dict(verification=v,python_executable=sys.executable,'
            'python_version=platform.python_version(),python_implementation=platform.python_implementation())))')
    result=subprocess.run([str(verification_python),'-c',script,str(directory)],cwd=ROOT,
                          check=True,capture_output=True,text=True)
    verified=json.loads(result.stdout)
    expect(verified['verification'].get('valid') is True,'Full scientific verification failed')
    expect(before==input_hashes(directory) and sources==source_hashes(directory),'Inputs changed during scientific verification')
    value=dict(schema_version=1,kind='swarm-ledger-verified-public-input',inputs=before,
               scientific_sources=sources,scientific_runtime=verified)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    return value


def check_receipt(directory,receipt):
    value=read(receipt)
    expect(set(value)=={'schema_version','kind','inputs','scientific_sources','scientific_runtime'} and
           type(value['schema_version']) is int and value['schema_version']==1 and
           value['kind']=='swarm-ledger-verified-public-input','Scientific input receipt schema differs')
    expect(value['scientific_runtime']['verification'].get('valid') is True,'Scientific input receipt is not successful')
    expect(value['inputs']==input_hashes(directory),'Stale scientific inputs: full verification receipt differs')
    expect(value['scientific_sources']==source_hashes(directory),'Scientific source changed after verification')
    return value


def load_cases(directory,receipt):
    check_receipt(directory,receipt);directory=Path(directory);manifest=read(directory/'manifest.json')
    cases=[]
    for profile in PROFILES:
        for part in manifest['artifacts']['cases:'+profile]:
            name=part['file'];expect(Path(name).name==name,'Public shard path invalid')
            path=directory/name;expect(digest(path)==part['sha256'],'Public case checksum differs')
            cases.extend(json.loads(line) for line in path.read_text(encoding='utf-8').splitlines())
    return cases,read(directory/'report.json')


def composition(cases):
    """All assigned FULL16 arms; categories exhaust every parsed verdict."""
    groups=defaultdict(list)
    for c in cases:
        if c['view']=='full':groups[(c['profile_id'],c['procedure'])].append(c)
    expect(set(groups)=={(p,d) for p in PROFILES for d in ('direct','procedure')},'FULL profile/procedure grid differs')
    out={}
    for key,rows in groups.items():
        expect(len(rows)==2560 and len({r['id'] for r in rows})==2560 and
               len({r['source_id'] for r in rows})==2560 and len({(r['block_id'],r['arm']) for r in rows})==2560 and
               len({r['block_id'] for r in rows})==640 and {r['arm'] for r in rows}==ARMS,'FULL assigned denominator differs')
        counts=[0,0,0,0]
        for c in rows:
            pred=c['raw_label']
            if c['correct_definite']:index=0
            elif pred in ('A','B','C','D','E','NONE'):index=1
            elif pred=='ABSTAIN':index=2
            elif pred=='INVALID':index=3
            else:raise ValueError('Unknown verdict category')
            counts[index]+=1
        expect(sum(counts)==len(rows),'Verdict categories do not exhaust assigned cases')
        out[key]=dict(counts=counts,n=len(rows),blocks=640,rates=[v/len(rows) for v in counts])
    return out


def acquisition(cases):
    """FULL and all six auxiliary views use the same honest+both subset."""
    profiles=('g26','q397','ds_low');groups=defaultdict(list)
    for c in cases:
        if c['profile_id'] in profiles and c['procedure']=='direct' and c['arm'] in ('honest','both'):
            groups[(c['profile_id'],c['view'])].append(c)
    expected={(p,v) for p in profiles for v in VIEWS}
    expect(set(groups)==expected,'Matched acquisition grid differs')
    out={p:[] for p in profiles};identities=None;oracle=[]
    for view in VIEWS:
        answerable=None
        for p in profiles:
            rows=groups[(p,view)];ids={(r['source_id'],r['block_id'],r['arm']) for r in rows}
            expect(len(rows)==len(ids)==1280 and len({(r['block_id'],r['arm']) for r in rows})==1280 and
                   len({r['block_id'] for r in rows})==640,'Acquisition assigned denominator differs')
            if identities is None:identities=ids
            expect(ids==identities,'Acquisition views do not share the same assigned sources')
            current={r['source_id']:(bool(r['answerable']),tuple(r['compatible_labels'])) for r in rows}
            if answerable is None:answerable=current
            expect(current==answerable,'Oracle support differs across readers')
            out[p].append(sum(r['correct_definite'] for r in rows)/1280)
        oracle.append(sum(flag for flag,_ in answerable.values())/1280)
    return dict(profiles=out,oracle=oracle,n=1280,blocks=640,views=VIEWS)


def procedure_effects(report):
    out=[]
    for p in PROFILES:
        row=report['primary'] if p=='g26' else report['secondary_procedure_effects'][p]
        expect(row['blocks']==640 and row['strata']==40 and row['draws']==10000 and row['seed']==730009,
               'Paired bootstrap definition differs')
        values=[row[k] for k in ('estimate','lower','upper')]
        expect(all(isinstance(v,(int,float)) and math.isfinite(v) for v in values) and values[1]<=values[2],
               'Invalid paired effect/interval')
        out.append(dict(profile=p,estimate=values[0],lower=values[1],upper=values[2]))
    return out


def plotting():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.labelsize':12,
                         'xtick.labelsize':12,'ytick.labelsize':12,'legend.fontsize':12,
                         'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white',
                         'svg.fonttype':'none','svg.hashsalt':'swarm-ledger-figures-v1'})
    return plt,matplotlib


def save(fig,directory,stem,plt):
    out=[]
    for suffix in ('png','svg'):
        path=Path(directory)/(stem+'.'+suffix)
        fig.savefig(path,dpi=300,facecolor='white',transparent=False,
                    metadata={'Date':None} if suffix=='svg' else {'Software':'swarm-ledger scientific figures'})
        out.append(dict(file=path.name,sha256=digest(path),bytes=path.stat().st_size))
    plt.close(fig);return out


def workflow(plt):
    from matplotlib.patches import FancyBboxPatch
    fig=plt.figure(figsize=(6.5,3.5));ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    def box(x,y,w,h,text,color='white'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',
                                   facecolor=color,edgecolor='#46515b',linewidth=1))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=12)
    ax.text(.5,.955,'Untrusted notes accompany bounded fake actions',ha='center',va='center',fontsize=12)
    labels=('Principal','Coordinator','X executor','Y executor','Reporter')
    for i,label in enumerate(labels):
        x=.025+i*.195;box(x,.73,.17,.14,label)
        if i<4:ax.annotate('',xy=(x+.19,.80),xytext=(x+.172,.80),arrowprops={'arrowstyle':'->','color':'#46515b'})
    ax.text(.5,.66,'Host executes role-specific choices',ha='center',va='center',fontsize=12)
    box(.045,.365,.91,.22,'Authentic host records establish bounded effects\nIssuance, grants, commits, clock, revocation, identities','#edf3f7')
    ax.annotate('',xy=(.5,.59),xytext=(.5,.635),arrowprops={'arrowstyle':'->','color':'#46515b'})
    box(.035,.06,.425,.19,'Evidence acquisition\nWhich records are available?')
    box(.54,.06,.425,.19,'Evidence use\nWhich verdict is supported?')
    ax.annotate('',xy=(.245,.255),xytext=(.245,.36),arrowprops={'arrowstyle':'->','color':'#46515b'})
    ax.annotate('',xy=(.53,.155),xytext=(.47,.155),arrowprops={'arrowstyle':'->','color':'#46515b'})
    return fig


def composition_figure(values,plt):
    from matplotlib.ticker import PercentFormatter
    fig,ax=plt.subplots(figsize=(6.5,5.6));fig.subplots_adjust(left=.30,right=.94,top=.97,bottom=.22)
    colors=('#3679ab','#c46a39','#bec7ce','#424b53')
    names=('Correct definite','Wrong definite','ABSTAIN','INVALID')
    for i,p in enumerate(PROFILES):
        for procedure,offset,short in (('direct',-.16,'D'),('procedure',.16,'P')):
            left=0.;values_=values[(p,procedure)]['rates']
            for j,v in enumerate(values_):
                ax.barh(i+offset,v,height=.28,left=left,color=colors[j],edgecolor='white',linewidth=.4,
                        label=names[j] if i==0 and procedure=='direct' else None);left+=v
            ax.text(1.02,i+offset,short,transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=12)
    ax.set(yticks=range(8),yticklabels=[NAMES[p] for p in PROFILES],xlim=(0,1),xlabel='Share of all assigned calls')
    ax.invert_yaxis();ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xticks((0,.25,.5,.75,1))
    ax.legend(loc='upper center',bbox_to_anchor=(.43,-.14),ncol=2,frameon=False,columnspacing=1.1,handlelength=1.3)
    ax.spines[['top','right']].set_visible(False);return fig


def procedure_figure(values,plt):
    from matplotlib.ticker import MaxNLocator
    fig,ax=plt.subplots(figsize=(6.5,3.9));fig.subplots_adjust(left=.34,right=.97,top=.97,bottom=.24)
    for i,row in enumerate(values):
        color='#245f8a' if row['profile']=='g26' else '#46515b'
        ax.plot([100*row['lower'],100*row['upper']],[i,i],color=color,linewidth=1.5)
        ax.plot(100*row['estimate'],i,marker='D' if row['profile']=='g26' else 'o',color=color,markersize=6)
    ax.axvline(0,color='#9aa2a9',linestyle='--',linewidth=1)
    ax.set(yticks=range(8),yticklabels=[NAMES[p]+(' (primary)' if p=='g26' else '') for p in PROFILES],
           xlabel='Procedure − direct (percentage points)\n95% stratified block-bootstrap interval')
    lo=min([0]+[100*r['lower'] for r in values]);hi=max([0]+[100*r['upper'] for r in values]);pad=max(2,(hi-lo)*.12)
    bounds=(lo-pad,hi+pad);ax.set_xlim(*bounds)
    ax.set_xticks([v for v in MaxNLocator(5).tick_values(*bounds) if bounds[0]<=v<=bounds[1]])
    ax.invert_yaxis()
    ax.spines[['top','right']].set_visible(False);return fig


def acquisition_figure(values,plt):
    from matplotlib.ticker import PercentFormatter
    fig,ax=plt.subplots(figsize=(6.5,4.9));fig.subplots_adjust(left=.32,right=.94,top=.97,bottom=.25)
    series=([('Finite-domain answerability',values['oracle'],'#252a30','D','--')]+
        [(NAMES[p]+' direct',values['profiles'][p],color,marker,'-') for p,color,marker in
         (('g26','#3679ab','o'),('q397','#bd6b35','s'),('ds_low','#4a8068','^'))])
    for name,rates,color,marker,style in series:
        ax.plot(rates,range(7),label=name,color=color,marker=marker,linestyle=style,linewidth=1.25,markersize=6)
    ax.set(yticks=range(7),yticklabels=VIEW_NAMES,xlim=(-.02,1.02),xlabel='Share of matched assigned trajectories')
    ax.invert_yaxis();ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xticks((0,.25,.5,.75,1))
    ax.legend(loc='upper center',bbox_to_anchor=(.40,-.16),ncol=2,frameon=False,columnspacing=1.0,handlelength=1.4)
    ax.spines[['top','right']].set_visible(False);return fig


def generate(directory,receipt,output):
    proof=check_receipt(directory,receipt);cases,report=load_cases(directory,receipt)
    expect(report['source_blocks']==640 and report['reader_responses']==64000,'Frozen report population differs')
    values=composition(cases);acq=acquisition(cases);effects=procedure_effects(report)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    expect(not (output/PROVENANCE).exists(),'Figure provenance exists; choose a new output directory')
    for stem in ('ledger_workflow','ledger_full_composition','ledger_procedure_effect','ledger_acquisition'):
        for suffix in ('png','svg'):expect(not (output/(stem+'.'+suffix)).exists(),'Owned figure exists; choose a new output directory')
    plt,matplotlib=plotting();outputs=[]
    for stem,fig in (('ledger_workflow',workflow(plt)),('ledger_full_composition',composition_figure(values,plt)),
                     ('ledger_procedure_effect',procedure_figure(effects,plt)),('ledger_acquisition',acquisition_figure(acq,plt))):
        outputs.extend(save(fig,output,stem,plt))
    expect(proof['inputs']==input_hashes(directory) and proof['scientific_sources']==source_hashes(directory),'Inputs changed while plotting')
    metadata=dict(schema_version=1,kind='swarm-ledger-scientific-figures',inputs=proof['inputs'],
                  scientific_sources=proof['scientific_sources'],scientific_runtime=proof['scientific_runtime'],
                  input_receipt_sha256=digest(receipt),plot_code_sha256=digest(__file__),
                  plotting_runtime=dict(python=platform.python_version(),python_executable=sys.executable,matplotlib=matplotlib.__version__),
                  outputs=outputs,dimensions=dict(width_inches=6.5,png_dpi=300,background='opaque white'),
                  captions=dict(workflow='Static instrument diagram, not an empirical result.',
                    composition='FULL16 parsed verdict outcomes; D=direct, P=procedure. Each bar includes all2,560 assigned trajectories across640 base blocks; technical failures are retained. Levels are descriptive.',
                    procedure='Procedure−direct change in parsed correct-definite verdicts on FULL16; all4 arms averaged within each of640 blocks. Intervals come directly from the frozen10,000-draw stratified bootstrap report; secondary intervals are exploratory.',
                    acquisition='All7 views use the same honest+both subset:1,280 trajectories/640 blocks per profile. Models show DIRECT supported-correct definite decisions. The finite-domain reference shows answerability, not learned performance. Lines guide the eye; no independent-call confidence intervals are asserted.'))
    with (output/PROVENANCE).open('x',encoding='utf-8',newline='\n') as f:json.dump(metadata,f,indent=2);f.write('\n')
    return dict(generated=True,figures=4,files=len(outputs),provenance=str(output/PROVENANCE))


def verify_only(directory,receipt,output):
    proof=check_receipt(directory,receipt);output=Path(output);value=read(output/PROVENANCE)
    expect(value['kind']=='swarm-ledger-scientific-figures' and value['schema_version']==1,'Figure provenance identity differs')
    expect(value['inputs']==proof['inputs'] and value['scientific_sources']==proof['scientific_sources'] and
           value['scientific_runtime']==proof['scientific_runtime'] and value['input_receipt_sha256']==digest(receipt),
           'Figure input provenance is stale')
    expect(value['plot_code_sha256']==digest(__file__),'Plot code changed; figures must be regenerated')
    expected={stem+'.'+suffix for stem in ('ledger_workflow','ledger_full_composition','ledger_procedure_effect','ledger_acquisition') for suffix in ('png','svg')}
    expect({r['file'] for r in value['outputs']}==expected and len(value['outputs'])==8,'Figure output inventory differs')
    for row in value['outputs']:
        path=output/row['file'];expect(path.is_file() and not path.is_symlink() and digest(path)==row['sha256'] and
                                    path.stat().st_size==row['bytes'],'Figure output changed')
    return dict(valid=True,scope='input/source/code/output provenance hashes only; statistical replay not repeated')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('verify-input','generate','verify-only'))
    parser.add_argument('--public',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path);parser.add_argument('--verification-python',type=Path,default=Path(sys.executable))
    args=parser.parse_args()
    if args.command=='verify-input':result=verify_input(args.public,args.receipt,args.verification_python)
    else:
        expect(args.output is not None,'Explicit figure output directory required')
        result=generate(args.public,args.receipt,args.output) if args.command=='generate' else verify_only(args.public,args.receipt,args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
