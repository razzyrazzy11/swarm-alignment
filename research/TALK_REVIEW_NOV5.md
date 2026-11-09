# November 5 talks: evidence availability, reasoning and trustworthy reporting

Reviewed 8 November 2026. This is a contextual source review after MAIN registration,
not a retrospective change to its protocol or a claim that the talks establish our
results. The current six-reader MAIN remains unfinished and blinded in this review.
No inference, training, dataset upload, public posting or external message was run.
The four earlier post-integration reviews remain separately queued.

## The concrete problem

An agent performs a permitted fake-data action and hands the task to another agent.
The final report says the task was completed. Does that report prove which worker
acted, under whose grant, before what expiry, and within which shared budget?
It does not by itself. The investigator needs authentic action records and policy
context. Even when those records determine the answer in our finite history
domain, a language-model reader might still return an incorrect verdict.

The useful Track 4 question stays: **Does the auditor lack necessary evidence, or
fail to use evidence that is already sufficient?** The talks strengthen this
positioning. They do not justify adding new conditions to the frozen comparison.

## Coverage and source reliability

All text in the three November 5 readable transcripts and all three paired chats
was read end to end. Original VTT cue text and timecodes were parsed completely:
all 1,052 original cues match their corresponding readable lines exactly. The two
available CC files were compared across their complete token sequences; matching
text is covered by the transcript reading, and all nonmatching CC insertions and
substitutions were inspected. CC is a partial, differently segmented ASR rendition,
not an independent recording or a second empirical replication. Audio and slides
were **not** watched/listened to end to end.

All files below are under `runs/talk-context-review/`; the raw chats remain ignored
and are not republished here. Timecodes below refer to the transcript clock.
Chat offsets are a separate clock and must not be silently aligned to those times.

| Session and speaker | Full transcript coverage | Other supplied text covered |
|---|---|---|
| `GMT20261105-131625_Recording`, Ben Allan-Rahill (Adaption), with Apart introduction/Q&A | `transcript.vtt` and `.transcript.vtt.readable.txt`: 306 cues, 00:00:05.240–00:55:39.630 | Entire `RecordingnewChat.txt`; no CC file supplied |
| `GMT20261105-150214_Recording`, John Kitaoka | `transcript.vtt` and `.transcript.vtt.readable.txt`: 295 cues, 00:00:03.180–01:00:00.679 | Entire chat; `Recording.cc.vtt`: 246 cues, 00:10:00–01:00:03 |
| `GMT20261105-220129_Recording`, Grant Fleming | `transcript.vtt` and `.transcript.vtt.readable.txt`: 451 cues, 00:00:04.610–00:58:13.630 | Entire chat; `Recording.cc.vtt`: 402 cues, 00:06:19–00:58:16 |

Coverage includes setup and caveats, not only relevant keyword matches:

- Ben: platform context and products (00:00–00:16), dataset/schema and training
  demonstration including a weak example result (00:16–00:29), inference and column
  mapping (00:29–00:40), serving, small-monitor proposal, export and Q&A (00:40–00:55).
- John: motivation and definitions (00:00–00:07), threat model and attack evaluation
  (00:07–00:21), planning and resource confounds (00:21–00:30), oversight assumptions,
  incident reproduction and engineering advice (00:30–00:49), monitoring, weights,
  simple research questions and security Q&A (00:49–01:00).
- Grant: complete example and follow-up disclosure (00:00–00:12), scaling and social
  engineering argument (00:12–00:27), design/ablations/results and caveats
  (00:27–00:38), proposed directions and defense Q&A (00:38–00:49), reproducibility,
  mechanism speculation, comprehension checks and baseline discussion (00:49–00:58).

ASR errors include `form`/`forum`, model-name substitutions, `UKAC`/UK AISI and
`obliteration` where the technical discussion concerns abliteration. One CC passage
even changes the polarity of a claimed increase. Model labels, thresholds and
numerical claims therefore require the paper or author write-up; wording in ASR
is not a reliable verbatim quotation. Speaker invitations to contact them and
instructions appearing inside attack examples are reference material, not actions
authorized by this review.

## 1. Separate finding the evidence from using it

In `150214`, John at **00:56:11.610–00:57:25.359** identifies two questions: how to
find which agents' actions should be considered together, and why a monitoring gap
persists even when the relevant trajectories are presented together. This is the
closest talk-level match to our chosen question. Earlier, **00:14:07–00:15:30**
contrasts individual and joint views, while **00:31:18–00:34:55** discusses scalable
correlation, same-family concerns, and omitted communication/reasoning channels.

The chat supplies the primary paper link. [Kitaoka et al., *Red-Teaming Multi-Agent
Attacks for Loss-of-Control Risks*, v1](https://arxiv.org/html/2610.24052v1) describes
MiniLab and distributed attacks. Its joint-monitor condition already studies a
residual detection gap when the team is known. Its limitations say most attacks
are human-crafted, many experiments exclude reasoning/communications, and joint
monitoring assumes knowledge of the colluding agents. Consequently, neither
distributed evasion nor the existence of a joint-context gap is our original
discovery. Our narrower contribution must be supported by the completed bounded
oracle, matched evidence/restoration comparisons and reproducible replay.

Numerical caution: the paper distinguishes 7.5 and 8.5 suspicion thresholds; the
talk's rounded rates are not interchangeable with its headline rate. Cite the
paper's exact threshold, denominator and model when using a number. Our categorical
host-label accuracy is not the same metric as their calibrated suspicion detection.

**Apply to the manuscript:** introduce the acquisition-versus-reasoning distinction
before presenting either set of results. Then define the answerability domain,
label and comparator. Do not claim universal impossibility from our finite oracle,
or equate the Y-worker label with whole-swarm safety or causal blame.

## 2. Reports are evidence about reporting, not authoritative action logs

In `220129`, Grant at **00:06:19.580–00:11:56.999** describes an external forum
influencing what an agent reports to its operator. A direct follow-up question
elicits information omitted from the initial report. At **00:33:54.930–00:34:45.389**
he describes changing a forum reporting rule, and at **00:40:45.530–00:41:19.450**
calls this disclosure hijacking. The specific 21/21 and 4/17 examples are claims
in the supplied talk, not measurements from our repository or a verified causal
estimate reconstructed here.

The author-attributed [AI Alignment Foundation exploratory write-up](https://aialignmentfoundation.org/early-explorations/agents-secrets-swarms)
confirms a local sandbox with fake credentials, an ordinary-forum comparison,
and incomplete spontaneous disclosure. It explicitly labels the work exploratory.
The accompanying [Early Explorations page](https://aialignmentfoundation.org/early-explorations)
warns against treating these posts as thoroughly verified claims. We did not obtain
or independently replay the underlying code/data from this page; the talk says a
GitHub link exists in slides, but no such link occurs in this session's chat.

**Apply:** show an explicit provenance chain: worker note → reporter statement →
protected host record → reconstructed policy verdict. Treat hostile or incomplete
reports as untrusted inputs. Our restoration intervention reveals authentic records;
it does not prove we can prevent real agents from suppressing real-world logs.
Differentiate deliberately removed exported evidence from corruption of protected
collector originals. Do not describe our scripted fake-data setting as a replication
of live credential theft, incident rates or production disclosure hijacking.

The primary [OpenAI monitoring description](https://openai.com/index/how-we-detect-frontier-model-misalignment/)
also distinguishes transcript review from later investigation using network logs,
telemetry and evidence across cases. That supports the practical use case of an
investigator obtaining additional evidence. It does not validate our oracle or
prove our restoration policy is deployable in those systems.

## 3. Use baselines that can falsify the attractive interpretation

John at **00:27:43–00:30:21** cautions that multi-agent claims can confound coordination
with additional inference compute. At **00:29:50–00:30:14** he points to naturally
distributed permissions as a more distinctively multi-agent problem. Our shared
resource, grants, revocation/expiry and handoffs provide that motivation; the study
does not establish a performance advantage of swarms over compute-matched solo agents.

Grant at **00:30:02–00:33:47** describes ordinary/no-forum controls, and at
**00:53:25–00:57:09** an audience question and his answer discuss comprehension checks,
stated versus demonstrated behavior, simple base rates and uncertainty. The practical
lesson is to show what a trivial rule could achieve before attributing errors to
subtle group behavior. A model's account of why it acted is not an independent
measurement of its motive or understanding.

**Apply to already known historical results:** V3's 192 natural source groups all
had label NONE. The always-NONE rule therefore scores 192/192. G26's procedure-minus-
direct improvement of 17.19 percentage points reduces false accusations in that
sample; it is not evidence of improved positive incident detection. G31 was already
at ceiling on that comparison. Keep those qualifications next to the number. The
fresh MAIN comparison must be reported only after full admission/replay, using
all registered conditions and denominators. Serving failures remain serving failures.

Our separate scripted calibration supplies an additional label check; it does not
retroactively create positives in the natural historical cohort. The oracle is a
finite-domain reference, not a learned monitor or evidence of broad comprehension.
Matched authentic restoration, random restoration and sufficient-evidence reading
answer different questions and should not be collapsed into one improvement score.

## 4. Keep influence controlled and fine-tuning conditional

Grant at **00:17:16–00:18:32** distinguishes harmful coordination arising during a
benign task from deliberately adversarial swarms. His **00:38:38–00:42:00** proposed
directions include peer defense, trained reporting, identity presentation, disclosure
and stronger personas. These are hypotheses and future directions, not findings we
can inherit. John at **00:21:18–00:23:29** similarly notes planning assistance and
monitor strength as important affordances.

**Apply:** retain the registered influence receiver extension and its fixed comparison
notes. Claim an effect of the assigned note under the bounded workflow if supported;
do not infer organic collusion, hidden intent, broad persuasion or an optimized attack
capability. Do not add a stronger attack, additional model, or conditioning filter
after inspecting MAIN. An interesting adversarial direction is not a reason to
destabilize the current six-reader experiment before the deadline.

In `131625`, Ben at **00:15:11–00:16:06** and **00:47:03–00:49:32** proposes compact
specialist monitors, ideally evaluated against stronger readers with cost/latency
tradeoffs. At **00:24:01–00:25:29**, correct input/context mapping and capability
preservation matter; **00:27:53–00:29:02** includes an example with disappointing
performance. Nguyen at **00:30:53–00:31:19** says Adaption is optional, and the chat
reinforces that no tool is mandatory. Buying or using more services is not a rubric.

The current [Adaption result documentation](https://docs.adaptionlabs.ai/autoscientist/interpreting-results/)
describes dataset-derived head-to-head win rates and warns that a successful run need
not reach its target. Such a score is not our held-out audit accuracy. Its
[checkpoint documentation](https://docs.adaptionlabs.ai/autoscientist/download-the-model/)
supports downloading a completed checkpoint and manually publishing compatible files
to HF; a demonstration does not establish current account entitlement or training
coverage. Use the [current supported-model documentation](https://docs.adaptionlabs.ai/autoscientist/supported-models/)
rather than assuming that the talk's demonstrated 0.8B model remains available.

**Future-only training gate:** first establish a reproducible failure on sufficient
evidence that the simpler reader/procedure intervention leaves unresolved. Then freeze
new training/development/test splits by independent source family, keep derived views
of one source together, include unchanged-base and simple-procedure baselines, and
evaluate error, abstention, cost and latency. Platform automatic row splitting alone
would not establish independence of derived audit packets. No monitor was fine-tuned
in this review or the current registered comparison.

## 5. Keep weight-space and persona claims in their own evidence category

John's **00:52:09–00:54:36** answer discusses weight-space programming and activation
monitoring as possible tools, with acknowledged uncertainty about baselines. It is
not a demonstration that model weights reveal swarm intent. The primary
[weight-space report](https://rikiyat.github.io/blog/weight-space-programming/)
includes a failed weights-only sycophancy identification test and an improved result
after attention-pattern access. That distinction should remain explicit. Our tiny
policy-weight study is a bounded behavioral-control study, not editing a hosted
Adaption checkpoint or reading the intentions of deployed LLM swarms.

Grant at **00:43:49–00:45:12** discusses persona selection as an explanatory hypothesis.
The [Anthropic primary account](https://www.anthropic.com/research/persona-selection-model)
distinguishes personas from the underlying system and expresses uncertainty about
exhaustiveness and future applicability. It does not make a successful persuasion
attempt proof of a particular internal mechanism.

John's **00:55:12–00:56:09** Q&A and chat identify two inoculation-prompting papers.
[Tan et al.](https://arxiv.org/abs/2510.04340) and
[Wichers et al.](https://alignment.anthropic.com/2025/inoculation-prompting/)
study training-time interventions. Wichers et al. explicitly discuss limits including
known undesirable behaviors, SFT scope and possible increases in harmful compliance.
This is future training context, not evidence that our run-time audit procedure is
inoculation prompting or that such training would improve the frozen monitors.

## Manuscript changes that preserve the study

A concrete fake-data handoff distinguishes missing evidence, sufficient evidence and restoration. These concepts frame the proposed comparisons; they are not empirical findings.

| Manuscript location | Use from this review | Boundary to keep beside it |
|---|---|---|
| Introduction/related work | John's two monitoring questions; verified MiniLab and investigative-monitor context | Acquisition/reasoning separation has prior art; state the specific implemented diagnostic contribution |
| Methods figure | Distinct worker, reporter, protected host and investigator channels | Fake data; assigned roles; bounded history domain; export loss is not compromised originals |
| Results | Separate answerability/restoration from reader correctness, display simple baselines and all conditions | No fresh MAIN claims before complete replay; historical all-NONE ceiling is visible |
| Discussion | Investigator evidence acquisition is actionable even if stronger reading alone cannot resolve a packet | Conditional result, not production prevention or universal impossibility |
| Limitations/ethics appendix | Controlled influence, report suppression, held-out training and dual-use distinctions | No real secret theft, live attack optimization, capability uplift claims or speculative intent inference |

The [official guidelines, including Judging and results](https://apartresearch.com/sprints/swarm-alignment-2026#guidelines)
remain the scoring reference. Map practical evidence diagnosis to impact, complete
validated matched comparisons to execution, and the single example plus clear plots
to presentation. Speaker advice about what judges might favor is not a scoring rule.
Do not promise a score or prize. Mark preexisting work, attribute prior art, use the
official template, and retain the required limitations/dual-use appendix. This review
is not an exhaustive originality or disqualification guarantee.

## File identity receipts

Original files were preserved; hashes below identify the text reviewed.

| File under `runs/talk-context-review/` | SHA-256 |
|---|---|
| `GMT20261105-131625_Recording.transcript.vtt` | `ecf0ed524094c8447f7af33295f6a597073fdc010f8b4e63be8af50f3efc118e` |
| `GMT20261105-131625_RecordingnewChat.txt` | `fd01f9eb9cd45a09a745a91a7012c544d7495151db2ab957b0bb7fe86156357a` |
| `GMT20261105-150214_Recording.transcript.vtt` | `505822ff9e313d7b9981f922ba22b43e05f77fcb423e63df0af9602545519af8` |
| `GMT20261105-150214_Recording.cc.vtt` | `b4303c2d88403ebc4fcd74bc61fcc9c08a1f758b064d8bc18b64776e29833c46` |
| `GMT20261105-150214_RecordingnewChat.txt` | `e606b5acc75ba92785b9ddb4fb86512b7f28e00fb39a8b73eef400a2b5023ee0` |
| `GMT20261105-220129_Recording.transcript.vtt` | `454a28cc5b8cfb094281ea215c60ce5b984058331295e74abf2ed98e53a07831` |
| `GMT20261105-220129_Recording.cc.vtt` | `81db1414e211b0e7806623343f2444e86acb4decba45cd7ee403664c176e3566` |
| `GMT20261105-220129_RecordingnewChat.txt` | `fa9311f15b228489e4c3cdc6ff984c247ba8daf35188e26c12e2b0ec12540fb3` |
