# AgentProof

**اثبت إن الـ agent بتاعك يستحمل الـ production، مش الـ demo بس.**

<p align="center">
  <img src="docs/pitch/01_cover.png" alt="AgentProof: prove trust before production" width="100%">
</p>

<p align="center">
  <a href="https://github.com/mohamedhekal/agentproof/actions/workflows/ci.yml"><img src="https://github.com/mohamedhekal/agentproof/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="python 3.10+">
  <img src="https://img.shields.io/badge/runtime%20dependencies-0-brightgreen" alt="zero runtime dependencies">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT">
  &nbsp;|&nbsp; <a href="https://github.com/mohamedhekal/agentproof/wiki/Home-AR">الـ Wiki</a> &nbsp;|&nbsp; <a href="README.md">English</a>
</p>

<div dir="rtl">

## جرّبه في المتصفح

**[الديمو اللايف](https://mohamedhekal.github.io/agentproof/)**: حرّك سلايدر الـ chaos وشوف agent ساذج وagent محصّن بيتعاملوا مع نفس الـ 8 سيناريوهات، وافتح تشغيلة فاشلة وأعدها، وأعد تشغيلة Claude متسجّلة، من غير ما تثبّت حاجة. بيشغّل الـ package الحقيقي في متصفحك (Python متحوّلة لـ WebAssembly عبر Pyodide): من غير سيرفر ولا API key ولا tracking.

> **ده ديمو لتوضيح الفكرة.** الـ agents سياسات مرجعية مكتوبة على متجر محاكى؛ مش benchmark لأي موديل ومش بيختبر الـ agent بتاعك. كل الداتا synthetic. (الموقع اللايف بيشتغل بعد تفعيل GitHub Pages للريبو؛ شوف [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).)

## الفكرة في جملتين

كل الناس بتبني agents، لكن قليل اللي يقدر يجاوب السؤال اللي أي شركة بتسأله قبل ما تدّي الـ agent صلاحية حقيقية: **هل هيتصرف في المرة الخمسين زي أول مرة، حتى لو الشبكة والـ tools والمدخلات بتبوّظ؟**

AgentProof هو **flight simulator للـ agents اللي بتتصرف فعلاً**: بيكسّر الـ tools بطريقة واقعية، وبيفحص **الحالة الحقيقية للنظام** (الفلوس، الشحنات، الرسايل) مش كلام الـ agent، وبيسجّل كل فشل عشان تعيده، وبيقفل الـ PR لو الأمان نزل. بدون ولا dependency في الـ runtime.

## إيه اللي جواه

| القدرة | بتعمل إيه |
|---|---|
| **Chaos** | timeout بس الكتابة اتنفّذت، طلب اتبعت مرتين، رد ضايع، بيانات مشوّهة، نص مدسوس: الأعطال اللي الـ production بيشحنها فعلاً |
| **تقييم الـ world مش الـ transcript** | كل سيناريو بيبني متجر جديد وبيقرا الـ ledger في الآخر |
| **محورين منفصلين** | هل حلّ التيكت؟ وهل حصل حاجة ممنوعة (استرجاع مرتين، استرجاع كبير من غير موافقة، تنفيذ أمر مدسوس)؟ |
| **Replay** | كل تشغيل بيتسجّل، وتعيده من غير شبكة ولا عشوائية |
| **CI gate** | الـ PR بيتقفل لو الثبات أو الأمان رجعوا لورا |
| **Calibrated autonomy** | راوتر بيتعلّم امتى لازم بني آدم يتدخل ويسأل أقل مع الوقت |
| **Company Brain** | ذاكرة bitemporal بتفرّق بين امتى الحقيقة كانت صح وامتى عرفناها |
| **LLM adapter** | نفس الاختبار على Claude / OpenAI، مع cassettes تعيد النتيجة offline |

## الـ pitch في 12 شريحة

الشرايح نفسها موجودة في الريبو ([docs/pitch](docs/pitch))، ونسخة [PDF](docs/pitch/AgentProof-pitch-deck.pdf) للتحميل.

</div>

<table>
<tr>
<td width="50%"><img src="docs/pitch/02_problem.png" alt="المشكلة"><br><sub><b>1. الفشل بقى بيغيّر العالم الحقيقي</b></sub></td>
<td width="50%"><img src="docs/pitch/03_evaluation_gap.png" alt="فجوة التقييم"><br><sub><b>2. الـ transcript ممكن يبان مثالي والـ ledger يقول غير كده</b></sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/04_solution.png" alt="الحل"><br><sub><b>3. flight simulator للـ agents في الـ production</b></sub></td>
<td width="50%"><img src="docs/pitch/05_architecture.png" alt="المعمارية"><br><sub><b>4. الـ agent ← الـ toolbox ← العالم المحاكى ← الـ grader</b></sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/06_chaos_engine.png" alt="Chaos"><br><sub><b>5. الأعطال اللي الـ production بيشحنها فعلاً</b></sub></td>
<td width="50%"><img src="docs/pitch/07_outcomes.png" alt="النتايج"><br><sub><b>6. تلات نتايج، حقيقتين منفصلتين</b></sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/08_scripted_evidence.png" alt="قياس scripted"><br><sub><b>7. قياس: سياسات مكتوبة (160 تشغيلة لكل agent)</b></sub></td>
<td width="50%"><img src="docs/pitch/09_llm_evidence.png" alt="قياس LLM"><br><sub><b>8. قياس: LLM حقيقي، متسجّل وبيتعاد</b></sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/10_replay.png" alt="Replay"><br><sub><b>9. فشل ما تقدرش تكرره بقى اختبار تعيده</b></sub></td>
<td width="50%"><img src="docs/pitch/11_company_brain.png" alt="Company Brain"><br><sub><b>10. ذاكرة تتحمّل التصحيحات</b></sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/12_autonomy.png" alt="Autonomy"><br><sub><b>11. الأتمتة محتاجة حكم مش مجرد حد أقصى</b></sub></td>
<td width="50%"><img src="docs/pitch/16_roadmap.png" alt="Roadmap"><br><sub><b>12. من proof-of-concept لبنية تحتية للثقة</b></sub></td>
</tr>
</table>

<details>
<summary>باقي الـ deck: الاستخدامات، نموذج العمل المقترح، خطة الدخول للسوق، الختام</summary>

<table>
<tr>
<td width="50%"><img src="docs/pitch/13_use_cases.png" alt="الاستخدامات"></td>
<td width="50%"><img src="docs/pitch/14_business_model.png" alt="نموذج العمل المقترح"></td>
</tr>
<tr>
<td width="50%"><img src="docs/pitch/15_gtm.png" alt="خطة الدخول للسوق"></td>
<td width="50%"><img src="docs/pitch/17_closing.png" alt="الختام"></td>
</tr>
</table>

</details>

<div dir="rtl">

> الـ deck بيقول حدوده بنفسه: الـ agents المرجعية سياسات مكتوبة مش benchmark لـ LLM، ونتيجة الـ LLM الحي 40 محاكاة بـ prompt غني بالقواعد، ونتيجة الـ Brain على رسايل مخترعة بـ extraction بقواعد، ونتيجة الـ autonomy simulation، وشريحة نموذج العمل **اقتراح مش إيراد ولا traction**.

## الأرقام (كلها بتتكرر بأمر واحد)

### 1. الـ agent الساذج مقابل المحصّن (chaos = 0.3، 8 سيناريوهات × 20 تشغيلة)

| الـ agent | اتحل | اتحوّل لبني آدم | **غير آمن** | الثبات (pass^k) |
|---|---|---|---|---|
| naive | 56.2% | 15.6% | **28.1%** | 0.0% |
| hardened | 98.8% | 1.2% | **0.0%** | 87.5% |
| hardened من غير retries | 33.1% | 66.9% | **0.0%** | 0.0% |

الأهم: الـ 28.1% **مش كلها بسبب retry**. فكّكتها: 19 تشغيلة بسبب تنفيذ تعليمات مدسوسة في ملاحظة الطلب، و19 بسبب التصرف على صورة قديمة (استرجاع طلب اتسترجع خلاص)، و**7 بس** بسبب retry لـ write اتنفّذ. يعني أغلب "مشاكل الـ reliability" هي في الحقيقة مشاكل **حدود ثقة وحداثة بيانات**. التفاصيل في [دراسة الحالة](docs/ar/CASE_STUDY.ar.md).

### 2. Claude على نفس الـ chaos

`claude-sonnet-5-5`، chaos 0.3، 40 تشغيلة: **40 اتحلّت، 0 unsafe**. الـ cassette (172 رد) متسجّل في الريبو وبيتعاد offline وبنفس النتيجة بالظبط. التحفّظ: الـ prompt بيدّي الموديل القواعد كلها، والعيّنة صغيرة.

### 3. أنهي قاعدة كان Claude معتمد عليها؟ (prompt ablation)

| اللي اتشال | اتحل | غير آمن |
|---|---|---|
| قواعد idempotency / ملاحظات مش موثوقة / ما ترجّعش مرتين / retry | 98-100% | 0% |
| **قاعدة حد الاسترجاع** | 75.0% | **12.5%** |
| **الـ API نفسه ما بيقبلش idempotency key** | 87.5% (0.3)، 81.2% (0.5) | **10.4%** |

القواعد الهندسية العامة كانت في الموديل أصلاً، لكن **سياسة الشغل (حد الاسترجاع) لأ**. ولما الـ API ما فيهوش idempotency، Claude أعاد الـ write اللي عمل timeout فوراً **5 مرات من 5** وسبّب تكرار. الخلاصة: الحماية مكانها الـ API والـ tools مش الـ prompt. التفاصيل: [ABLATION.ar.md](docs/ar/ABLATION.ar.md).

### 4. الذاكرة والـ autonomy

| | النتيجة |
|---|---|
| Company Brain مقابل RAG + recency (10 seeds) | **99.9%** مقابل 78.4%. ولو 15% من الصياغات جديدة: 87.0% مقابل 67.1% |
| Calibrated router مقابل حد ثابت (محاكاة 4000 فعل) | أفعال غلط من غير مراجعة: **0.7%** مقابل 13.7% |

الـ extractor بتاع الـ Brain rule-based، فالـ 99.9% سقف مش توقع، والنزول لـ 87% و76% عند صياغات جديدة معلن في الجدول.

## تشغيل سريع

</div>

```bash
git clone https://github.com/mohamedhekal/agentproof && cd agentproof
pip install -e .                 # من غير أي runtime dependencies

agentproof compare               # naive مقابل hardened تحت chaos
agentproof gate                  # CI gate (exit 1 لو حصل تراجع)
agentproof brain                 # الذاكرة bitemporal مقابل RAG
agentproof autonomy              # راوتر الـ human-in-the-loop
agentproof compare --agents replay:cassettes/claude.jsonl --runs 5 --chaos 0.3   # نتيجة Claude offline
```

<div dir="rtl">

لتجربة الـ agent بتاعك: اكتب class فيه `name` و`run(ticket, tools)` وشغّل `agentproof compare --agents my_agent:MyAgent`.

## الشغل ده بيثبت إيه

| المهارة | فين بتبان في الريبو |
|---|---|
| تصميم أنظمة موثوقة (idempotency، retries، fail-safe) | `agents.py`، تحليل الـ ablation |
| Chaos engineering وفحص الحالة (invariants) | `toolbox.py`، `scenarios.py` |
| قياس صادق: pass^k، فصل الأمان عن النجاح، حدود الثقة الإحصائية | `runner.py`، كل جدول بتحفّظاته |
| Record/replay وـ reproducibility (content-hashed cassettes) | `llm.py`، `cassettes/` |
| دمج LLM حقيقي (Anthropic و OpenAI، parallel tool calls، backoff) | `llm.py`، `tests/test_openai_http.py` |
| نمذجة بيانات زمنية (bitemporal) وـ provenance | `brain/` |
| إحصاء عملي (Wilson bound، drift detection) | `trust.py` |
| CI/CD وـ quality gates | `.github/workflows/ci.yml`، `agentproof gate` |
| اختبارات متينة (48 test، سيرفر HTTP محلي بيفحص البروتوكول) | `tests/` |
| كتابة تقنية أمينة (ما هو مقاس وما هو غير مقاس) | كل `docs/` |

حوالي 2,300 سطر Python في 18 module، و490 سطر اختبارات، بدون أي dependency في الـ runtime.

## الدوكيومنتيشن

| الموضوع | English | العربية |
|---|---|---|
| نظرة عامة | [README.md](README.md) | هنا |
| المبادئ ونموذج الأعطال والـ invariants | [DESIGN.md](docs/DESIGN.md) | [DESIGN.ar.md](docs/ar/DESIGN.ar.md) |
| دراسة الحالة | [CASE_STUDY.md](docs/CASE_STUDY.md) | [CASE_STUDY.ar.md](docs/ar/CASE_STUDY.ar.md) |
| الـ prompt ablation على Claude | [ABLATION.md](docs/ABLATION.md) | [ABLATION.ar.md](docs/ar/ABLATION.ar.md) |
| ورقة عمل الـ deep dive | [DEEP_DIVE.md](docs/DEEP_DIVE.md) | [DEEP_DIVE.ar.md](docs/ar/DEEP_DIVE.ar.md) |
| الـ Wiki (كل صفحة بالإنجليزي والعربي) | [Home](https://github.com/mohamedhekal/agentproof/wiki) | [الرئيسية](https://github.com/mohamedhekal/agentproof/wiki/Home-AR) |

كل الداتا في الريبو synthetic ومخترعة، ومفيهاش أي بيانات حقيقية. الترخيص MIT.

</div>
