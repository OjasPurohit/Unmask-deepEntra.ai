# Brief for ChatGPT: write the content for our hackathon pitch deck

> **How to use:** paste this whole file into ChatGPT, then send: *"Write the slide content following this brief."*

---

## Your task
You are an expert pitch-deck writer for technical hackathons. Write the **text content for an 8-slide deck** (titles, bullet points, speaker notes, visual suggestions) for our team's **11:00 AM solution presentation**. At that point we present our *problem, proposed AI solution and build plan* to judges before building starts.

**Critical rule: nothing has been built yet.** The build starts at 12:15 PM, after this presentation. Write everything as **"we will build / our approach / our plan"**. Never imply existing code, results, screenshots, accuracy numbers or a working prototype.

---

## The event
- **deepEntra Build Fest 2026**, a one-day AI hackathon in Pune, India, hosted at **Vidyarthi Sahayyak Samiti (VSS)**, a Pune student-support institution that runs hostels and a multi-step student admission process (applications, documents, interviews).
- Slogan: *"Build real ideas. Ship working AI."*
- Build window: about 3 hours. Final demos to judges at 4:00 PM.
- **The 11:00 presentation is short (about 2–3 minutes).** Slides must be scannable: at most 3–4 short bullets each.

### Judging criteria (every slide should serve one of these)
| Criterion | Weight | What judges want |
|---|---|---|
| Innovation & originality | 30% | A smarter or different approach than the obvious one |
| Technical execution | 25% | Does it work? Good use of AI in the time available |
| Real-world impact | 25% | Practical value **for VSS or its community** |
| Demo & presentation | 20% | Clear story, clearly shown |

### The judges
- **VSS trustees** (Dr Jyoti Gogte, Tushar Ranjankar): care about impact for VSS students and admissions.
- **Enterprise security and IT architects** (e.g. an IBM security-governance manager): care about guardrails, auditability, honest confidence, false positives.
- **Product leaders** from fintech, SaaS and ServiceNow backgrounds: care about the user, the workflow and a clear story.
- **deepEntra founder**: cares about shipping real, working AI.

---

## The challenge we picked: CYB-03 (Advanced Challenge)
**Explainable Deepfake & Digital Identity Manipulation Detection**
- *Context:* Face swaps, synthetic media and manipulated identity content can undermine trust in interviews, verification, social media and digital evidence.
- *Challenge:* Build a defensive system that analyzes image/video samples for manipulation signals and reports **where and why** content appears suspicious, with confidence, failure cases and human review.
- *Must show:* (1) evaluation on a real vs manipulated sample set, (2) frame/region-level evidence or indicators, (3) accuracy, false positives and limits.
- *Guardrail:* **Detection is probabilistic. Do not present the result as proof of identity or wrongdoing.**

---

## Our product: **UNMASK**
- Tagline options: *"See where. See why."* / *"Every face tells a story. We check if it's true."*
- Team: **Team Masons**, Ojas Purohit (team lead / architect), Omkar Patil (AI models), Yadnesh (backend & ML), Palash (frontend / UI).

### One-line pitch
A screening assistant that analyzes a photo or video of a person and shows **where** it looks manipulated, **why**, **how confident** it is, and **hands the decision to a human**.

### The VSS use case (lead with this)
VSS admits students through applications, ID photos and interviews. A face-swapped ID photo, an AI-generated applicant photo or a manipulated video submission can now be made in seconds with free apps. Unmask gives the admissions or verification desk a second pair of eyes. **It flags and explains. It never accuses and never decides.**

### What we WILL build (planned features)
1. **Upload** an image or video.
2. **Where:** a heatmap over the face showing suspicious areas; a ranking of face regions (eyes, mouth, jaw boundary, skin); for video, a timeline showing which frames look suspicious.
3. **Why:** five independent forensic signals, each with a one-line plain-English reason:
   - **AI classifier**: two complementary pretrained vision models (one strong on AI-generated/edited images, one face-focused classifier we will train for face swaps).
   - **Error Level Analysis**: edited regions re-compress differently.
   - **Frequency analysis**: AI generators leave unnatural patterns in the image's frequency spectrum.
   - **Noise consistency**: a pasted face has different camera "grain" than the background.
   - **Metadata check**: camera info, editing-software tags, content credentials.
   - Video extras: blink rate and facial jitter across frames.
4. **How sure:** the signals combine into one calibrated confidence score and a band:
   - "No strong manipulation indicators found"
   - "Inconclusive — human review required"
   - "Strong manipulation indicators — human review required"
5. **Who decides:** a human review queue (agree / disagree / needs more evidence, with notes), a full audit log, and a **SHA-256 fingerprint** of every file for evidence integrity.
6. **Plain-English explanation:** a language model rewrites the *measured* results into a short paragraph. It never sees the image and never makes the decision.
7. **Honest evaluation page:** accuracy, **false-positive rate**, results per manipulation type, robustness to compression, and a **gallery of cases the system gets wrong**.
8. **Stretch goal:** an Android app so a verification officer can check a photo from a phone.

### Why our approach is different (for the innovation slide)
- Most deepfake tools output one opaque score ("87% fake"). Unmask shows **where + why + how sure + who decides**.
- **Known industry problem:** published deepfake detectors often fail on manipulation types they weren't trained on. One model means one blind spot. **Our approach:** several independent signals, including two complementary AI models, combined, and we will *measure* whether combining beats any single signal.
- **We plan against a classic shortcut:** we crop to the face before analysis so the AI judges the face, not image size or background.
- **False positives are treated as the most important metric**, because wrongly flagging an honest applicant is the worst outcome for VSS.
- **Runs locally:** images never leave the verification machine (privacy by design).

### How we'll evaluate
- A held-out test set of **real vs manipulated faces** from public research datasets (DeepFakeFace: face swaps, inpainting, fully AI-generated faces; DFDC video samples), plus our own consented photos as an "unseen data" check.
- We will report accuracy, precision, recall, **false-positive rate**, per-type results, robustness to compression and resizing, and failure cases with reasons.

### Guardrails (must appear in the deck)
- Never labels anything "fake", "proof" or "guilty". Only "manipulation indicators".
- The "inconclusive" band always routes to a human.
- The system supports a reviewer; the **human makes the final decision**.
- Disclaimer used in the product: *"Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."*

### Build plan (today)
| Person | Will build |
|---|---|
| Ojas | Architecture, integration, evaluation & review screens, demo |
| Omkar | AI models: detectors, heatmaps, training, evaluation |
| Yadnesh | Forensic signals, video analysis, explanations, database |
| Palash | UI: upload flow, evidence report, design |
- Milestones: **1:45** first image analysed end-to-end · **2:45** video + evaluation results · **3:30** feature freeze · **4:00** demo.
- Stretch: Android app.

### Next steps after the hackathon
Pilot at the VSS admissions desk · more training data (e.g. FaceForensics++, Celeb-DF) · live interview liveness checks · C2PA content-credential verification.

---

## Slide structure to write
Write content for these 8 slides. **Slide 6 is already final: reproduce it exactly as given, don't rewrite it.**

1. **Title**: name, one-line description, tagline, challenge code (CYB-03), team name and members.
2. **The problem**: framed around VSS admissions and digital trust; why a single score isn't enough.
3. **Our solution**: what Unmask will do (where / why / how sure / who decides).
4. **How it will work**: the pipeline in one flow (upload → fingerprint → face detection → 5 forensic signals → combined confidence → explanation → human review); suggest a simple diagram.
5. **Our approach / why it's different**: multi-signal instead of one model, complementary AI models, false positives first, face-crop shortcut guard, local and private.
6. **Tech stack**: FIXED, reproduce exactly:

   | Layer | Tools |
   |---|---|
   | AI / ML | PyTorch, Hugging Face Transformers (pretrained vision models: ViT, Swin), scikit-learn (training the combining model) |
   | Computer vision | MediaPipe Face Landmarker (478 face points), OpenCV (video frames, image forensics) |
   | Backend | Python, FastAPI, SQLite (cases + review audit log) |
   | Explanations | Gemini / Claude API, only rephrases measured results, with an offline fallback |
   | Frontend | React + TypeScript, Tailwind CSS, Recharts (graphs) |
   | Mobile (stretch) | Capacitor → Android app using the same interface |
   | Dev tools | GitHub, Antigravity, Claude Code |
   | Data | Public research datasets (DeepFakeFace, DFDC samples) + our own consented photos |

   Footer: *Runs locally: images never leave the verification machine.*
7. **Evaluation & guardrails**: what we will measure, and the responsible-AI rules.
8. **Build plan & impact**: who builds what, today's milestones, stretch goal, next steps, and a strong closing line tied to VSS.

## Output format I want from you
For **each slide**:
- **Title** (max 8 words, punchy)
- **On-slide text:** 3–4 bullets, max 12 words each (big-font friendly)
- **Visual suggestion:** a diagram, icon or layout idea
- **Speaker notes:** 2–4 sentences, about 20 seconds when spoken, conversational, confident

Then give:
- A **one-sentence closing line** for the presenter.
- **5 likely judge questions with short, honest answers** (e.g. "How accurate will it be?", "What if it's wrong?", "Why use an LLM?", "Is it private?", "What's the real use at VSS?").

## Style rules
- Confident but honest. No hype words like "revolutionary", "100% accurate", "guaranteed".
- **Never** say "detects fakes with certainty", "proves", "catches frauds" or "identifies criminals". Say "flags manipulation indicators", "supports human reviewers".
- **No invented numbers, results or progress.** Everything is future tense or a plan.
- Visual theme to suggest: dark navy background (#0B1220), off-white text, teal accent (#14B8A6), clean sans-serif (Space Grotesk / Inter), lots of whitespace.
