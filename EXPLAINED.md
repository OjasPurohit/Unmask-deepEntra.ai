# Unmask: the whole project explained from zero

This document assumes you know nothing. Read it top to bottom once and you'll understand the event, the problem, our solution, every technical idea behind it, what's already done, and exactly what happens today.

---

## 1. The 30-second version
- **Event:** deepEntra Build Fest 2026, a one-day AI hackathon in Pune (26 Sep 2026). Teams of 2–4 pick a problem, build a working AI prototype in about 3 hours, and demo it to judges.
- **Our problem (CYB-03):** detect whether a photo or video of a person has been manipulated (deepfakes, face swaps, AI-generated faces), and **explain where and why** it looks suspicious, with honest confidence levels and a human making the final call.
- **Our product:** **Unmask**, in the browser and as an Android app. You upload a photo or video. It runs several independent "forensic tests", paints a heatmap over the suspicious part of the face, explains in plain English what it found, gives a confidence level, and sends the case to a human reviewer. It also has a scoreboard page showing how accurate it is, including where it fails.
- **Why we can win:** most teams will show "a model that says 87% fake". We show *where* on the face, *why*, *how sure*, *how often we're wrong*, and *who decides*. That matches every line of the problem statement and every scoring criterion.

---

## 2. The hackathon itself

### 2.1 Schedule (today)
| Time | What happens | What it means for us |
|---|---|---|
| 9:30–10:00 | Reporting | Be there early, laptops charged. |
| 10:00 | Check-in & kickoff | Rules and judging briefing. |
| **11:00** | **Team solution presentations** | We present our *plan* (problem, idea, architecture, build plan). The deck must already be made. |
| 12:00 | Mentor feedback & **build lock** | Mentors comment, then we lock what we'll build. |
| **12:15** | **Build sprint starts** | Real coding starts here. |
| 1:30 | Lunch (keep building) | |
| **3:30** | **Build freeze** | No new features after this. Only testing and demo rehearsal. |
| **4:00** | **Final demos to judges** | The moment that matters. |
| 4:30 / 4:45 | Judging, winners | |

**Real build time is 12:15 to 3:30, about 3 hours 15 minutes.** Everything in this plan is sized for that.

### 2.2 How we're scored
| Criterion | Weight | In plain words |
|---|---|---|
| Innovation & originality | 30% | Did we solve it in a smarter or different way than the obvious one? |
| Technical execution | 25% | Does it actually work, live? Is the AI used well? |
| Real-world impact | 25% | Does it create real value, especially for **VSS** (Vidyarthi Sahayyak Samiti, the host institution) and its community? |
| Demo & presentation | 20% | Can we tell the story clearly and show it working? |

### 2.3 Who's judging (and what each type cares about)
17 panelists. They fall into groups:
- **VSS trustees** (Dr Jyoti Gogte, Tushar Ranjankar): care about *impact for VSS*. We tie our tool to VSS admissions, where students apply with ID photos and interviews.
- **Security / enterprise architects** (e.g. Mandar Modak at IBM, security governance): care about *guardrails, audit trails and honest confidence*. We give them a false-positive rate, an audit log and a SHA-256 fingerprint.
- **Product leaders** (Bapats, Baxi, Sumant, Kulkarni and others): care about *clear UX and a clear story*. Hence a polished UI and a scripted demo.
- **deepEntra founder** (Deepali Kulkarni): the event slogan is "Build real ideas. Ship working AI."

### 2.4 Rules that matter
- Teams of 2–4. AI tools (ChatGPT, Claude, Gemini, Cursor, Antigravity) are allowed.
- "Work should be created during the event unless otherwise permitted." So we prepared **research, environment, data, models, plans and prompts** in advance, but **the product code gets written today**.
- The CYB-03 guardrail: **"Detection is probabilistic. Do not present the result as proof of identity or wrongdoing."** We never say "fake", "proof" or "guilty" anywhere.

---

## 3. The problem, explained

### 3.1 What is a "manipulated" or "deepfake" image?
An image of a person altered or created by software, usually AI. Our test data has three kinds:
| Type | What it is | Everyday example |
|---|---|---|
| **Face swap** | Person A's face pasted onto person B's head/body, blended by AI. | Someone submits an ID photo with their friend's face swapped in. |
| **Inpainting** | Part of a real photo erased and repainted by AI (e.g. just the eyes or mouth changed). | A real photo with an altered feature. |
| **Text-to-image** | The whole photo generated from a text prompt. The person doesn't exist. | A fake applicant profile photo. |

Videos can have all of these, frame by frame.

### 3.2 What the challenge asks for, line by line
| The problem statement says | How we answer it |
|---|---|
| "Analyzes image/video samples for manipulation signals" | Upload an image or a video. Five independent forensic signals run on it. |
| "Reports **where** … content appears suspicious" | A heatmap over the face, a ranking of face regions (eyes, mouth, jawline…), and for video the exact suspicious frames. |
| "…and **why**" | Each signal gives a one-line reason in plain English, and an AI narrator writes a summary using only the measured facts. |
| "With confidence" | One calibrated percentage plus a band: clean / inconclusive / strong indicators. |
| "Failure cases" | An evaluation page with a gallery of cases we got *wrong* and the reason. |
| "Human review" | A review queue where a person agrees, disagrees or asks for more evidence. Every decision is logged. |
| "Evaluate real vs manipulated sample set" | We test on 350 real and 300 manipulated images plus 20 videos. |
| "Report accuracy, false positives & limits" | The evaluation dashboard: accuracy, false-positive rate, per-type results, robustness, limitations. |

### 3.3 Why this matters for VSS
VSS admits students through applications, documents and interviews. A face-swapped ID photo or an AI-generated applicant photo undermines that process. Unmask is a **screening assistant** for the admissions desk: it flags content that deserves a closer look. It never accuses anyone. A person always decides.

---

## 4. The product: what a user sees
1. **Analyze page:** drag in a photo or video, or click one of the sample files. A progress bar shows the steps: *Detecting face → Running 5 forensic signals → Fusing evidence → Writing explanation*.
2. **Evidence report page:**
   - A coloured banner, green, amber or red, with the exact wording:
     - Green: "No strong manipulation indicators found"
     - Amber: "Inconclusive — human review required"
     - Red: "Strong manipulation indicators — human review required"
   - The image with a **heatmap overlay** (red = the AI found this area suspicious) and a slider to fade it in and out.
   - **Region chips:** "jaw boundary 78%, mouth 41%, eyes 22%…"
   - **Signal cards:** one per forensic test, each with a score bar, a one-line reason and an image of what that test saw.
   - **Contribution bars:** which tests pushed the final score up the most.
   - For **video:** a timeline graph of suspicion over time. Click a spike to see that frame's heatmap.
   - A plain-English explanation, a list of limitations, a **SHA-256 fingerprint** of the file, the disclaimer, review buttons, and a Print button that produces a PDF report.
3. **Evaluation page:** our honest scoreboard. Accuracy, false-positive rate, a ROC curve, a confusion matrix, per-type results, robustness tests and a failure gallery.
4. **Review queue:** every analysed case, its band and the reviewer's decision, with a full audit trail.
5. **Settings:** one field to point the app at the verification machine (the laptop running the models). Only really needed on the phone, where the network address changes with the venue.

### 4.1 The phone app
The same product also installs on an **Android phone** as an app called Unmask. It is not a second app: a tool called **Capacitor** wraps the exact same React build into an APK. An admissions officer can photograph or pick an applicant photo on the phone and get the same evidence report.

**The AI does not run on the phone.** The phone sends the file to the verification laptop over the local Wi-Fi (or the phone's own hotspot), the laptop runs the models and sends back the result. That keeps the ~5 GB of models and the case database on one controlled machine, keeps the phone fast, and means the audit trail lives in one place. Details: `context/ANDROID_APP.md`.

---

## 5. How it works inside, piece by piece

### 5.1 Big picture
```
Browser (React UI)  ──upload──►  Backend server (Python, FastAPI)
  or Android app                     (the "verification machine" — models live here)
                                   1. Fingerprint the file (SHA-256)
                                   2. Find the face (MediaPipe)
                                   3. Run 5 forensic signals ─► each gives score + heatmap + reason
                                   4. Fuse the scores into one confidence (logistic regression)
                                   5. Pick the band (clean / inconclusive / strong)
                                   6. AI narrator writes the explanation (Gemini/Claude)
                                   7. Save the case for human review (SQLite)
Browser  ◄──JSON result + images──┘
```
- **Frontend** = what you see in the browser. Built with React (UI library), TypeScript (JavaScript with types), Tailwind (styling), Recharts (graphs). The Android app is this same frontend packaged by Capacitor; it just points at the laptop's address on the local network instead of at localhost.
- **Backend** = the Python program doing the analysis. FastAPI turns Python functions into web addresses such as `/api/analyze`.
- **API contract** = the agreed exact format of the data the backend sends to the frontend. We fixed it in advance (`context/FRONTEND_OJAS_PALASH.md`) so both halves can be built at the same time without waiting on each other.

### 5.2 Step 1: SHA-256 fingerprint
A mathematical fingerprint of the file. Change one pixel and the fingerprint changes completely. It proves the file the reviewer sees is exactly the file that was analysed, a basic idea in handling digital evidence ("chain of custody"). Cheap to add, and security judges like it.

### 5.3 Step 2: find the face (MediaPipe)
MediaPipe is a free Google library that finds a face and places **478 landmark points** on it (eye corners, lip edges, jawline…). From those points we:
- **crop** the face (a box 1.3× the face size) so the AI looks at the face, not the background;
- draw **region masks**: left eye, right eye, mouth, nose, jaw boundary, skin, background. That's how we can say "suspicion is concentrated at the jaw boundary". Face swaps often leave blending errors exactly along the jawline, so that finding is meaningful.

### 5.4 Step 3: the five forensic signals
Think of these as five different experts looking at the same photo. Each says "how suspicious (0–100%)", "where", and "why".

| # | Signal | Plain explanation | What it catches |
|---|---|---|---|
| S1 | **AI classifier** — two sub-scores. `cf`: the CommunityForensics model reading the **whole image** (one number = the probability it was manipulated). `probe`: our own small classifier trained on top of a big model's understanding of the **cropped face**. The suspicion we show is the higher of the two, and both go into the fusion step separately. The heatmap comes from **occlusion**: we cover small squares one at a time and watch how the score changes. If covering the jawline makes the score drop a lot, the jawline is where the AI saw the problem. | All three types; `cf` is strongest on generated and inpainted images, `probe` on face swaps. Together they are our strongest signal. |
| S2 | **Error Level Analysis (ELA)** | Re-save the JPEG and compare it with the original. Areas edited after the original save compress differently and "glow". | Pasted or edited regions. |
| S3 | **Frequency analysis (FFT)** | Convert the image into its "frequency fingerprint" (like turning sound into bass/treble). AI generators leave unnatural repeating patterns there. | AI-generated images. |
| S4 | **Noise consistency** | Every camera leaves fine grain ("noise"). If the face's grain differs from the background's, the face probably came from somewhere else. | Face swaps, splicing. |
| S5 | **Metadata** | Hidden info inside the file: camera model, editing software ("Photoshop", "Stable Diffusion"), content-credential tags. Missing camera info is a weak hint. | Edited or generated files; low weight. |

For **videos** we sample up to 16 frames, run the classifier on each (the **timeline**), and add two human-behaviour checks: **blink rate** (people blink about 15–20 times a minute and some deepfakes blink too little) and **landmark jitter** (a swapped face often wobbles slightly frame to frame).

We also run a **robustness check**: re-score the image after heavy compression and shrinking. If the score collapses, we warn that the result is fragile.

### 5.5 Step 4: fusion (combining the experts)
Six numbers (S1 contributes two, `cf` and `probe`, plus ELA, FFT, noise and metadata) become one score using **logistic regression**, a simple, explainable formula that learns from our test data how much to trust each signal. Because it's simple we can show **each signal's contribution** ("the face-crop probe added +31%, noise added +9%…").

### 5.6 Step 5: confidence bands
| Final score | Band | What the reviewer is told |
|---|---|---|
| under 35% | clean | No strong manipulation indicators found |
| 35–70% | inconclusive | Inconclusive — human review required |
| over 70% | strong | Strong manipulation indicators — human review required |
There's no "fake" band on purpose. Every result carries the disclaimer: *"Probabilistic forensic indicators only. Not proof of identity, authenticity or wrongdoing. Final decision rests with a human reviewer."*

### 5.7 Step 6: the AI narrator
A language model (Gemini or Claude) turns the measured numbers into a short paragraph a non-expert can read. **It never looks at the image and never decides anything.** It only rephrases facts we measured, so it can't invent evidence. If the internet or API fails, a built-in template writes the paragraph instead.

### 5.8 Step 7: human review and audit
Cases go into a queue. A reviewer clicks agree / disagree / needs more evidence and adds a note. Every action is logged with a time. This is the "human-in-the-loop" the problem statement demands.

---

## 6. The key concepts (glossary you'll need when judges ask)
| Term | Meaning |
|---|---|
| **Model** | A trained AI program. Input: an image. Output: a number. |
| **Classifier** | A model that sorts inputs into classes (real vs manipulated). |
| **Pretrained model** | A model someone else already trained and published (we get them from Hugging Face, an app store for AI models). |
| **Embedding** | A list of numbers (e.g. 768 of them) a model produces to describe an image: its "understanding" of the picture. |
| **Linear probe** | Take a pretrained model's embeddings and train a tiny, simple classifier on top, using *our* labelled examples. Fast (about a minute), cheap, and often very effective. |
| **Train / test split** | We learn from 70% of the data and measure on the other 30% the model never saw. Measuring on training data would be cheating. |
| **Cross-validation (5-fold)** | Do the split five different ways and average, for a more reliable number. |
| **Accuracy** | % of all images labelled correctly. |
| **False positive / FPR** | A **real** image wrongly flagged. For VSS this is the worst mistake: an honest student gets flagged. We report it prominently. |
| **False negative** | A manipulated image we missed. |
| **Precision / recall** | Of what we flagged, how much was really manipulated / of all the manipulated images, how many we caught. |
| **AUC** | One number for how well a model *separates* real from manipulated across all thresholds. **0.5 = coin flip, 1.0 = perfect.** Our main comparison number. |
| **ROC curve** | The graph behind AUC: catch rate vs false-alarm rate at every threshold. |
| **Threshold** | The cut-off score at which we flag something. We pick it so at most about 10% of real images get flagged. |
| **Confusion matrix** | A 2×2 table: real-called-real, real-called-manipulated, manipulated-called-real, manipulated-called-manipulated. |
| **Data leakage** | When a model learns an accidental shortcut instead of the real thing. See 7.3; we guard against it. |
| **Out-of-distribution** | Images unlike the training data (e.g. our own selfies). The honest way to show limits. |
| **Ensemble / fusion** | Combining several models or signals so one's weakness is covered by another's strength. |
| **Capacitor** | A tool that packages a normal web app into a real Android (or iOS) app, so one codebase ships to both. |
| **APK** | The installable file format of an Android app. |
| **LAN** | The local network (the Wi-Fi in the room). Our phone app talks to the laptop over it, never over the internet. |
| **GPU / CUDA** | Graphics card used to run AI fast. Ojas's laptop has an RTX 5050, and the code also runs (slower) on CPU. |

---

## 7. What we've done so far

### 7.1 Understanding and planning (25 Sep)
- Read the whole webpage (schedule, scoring, all 17 panelists, terms) and the full problem book.
- Chose the angle: a multi-signal, explainable, honestly evaluated forensic tool for VSS admissions.
- Wrote `PLAN.md` (strategy, architecture, timeline, demo script) and `CLAUDE.md` (full technical spec for the coding agents).

### 7.2 Environment and assets (Ojas's laptop)
- Python 3.12 environment (`.venv`) with PyTorch on the GPU, MediaPipe, Hugging Face Transformers, FastAPI and the rest, all tested.
- **Seven detector models downloaded** into `models/` (about 5.5 GB), plus MediaPipe's face model.
- **Test data downloaded** into `data/`: 350 real faces, 100 face swaps, 100 inpainted, 100 text-to-image (from the public research dataset *DeepFakeFace*), plus 10 real and 10 manipulated videos (from Facebook's *DFDC* challenge sample).

### 7.3 Research findings (the most important part)
**Finding 1: the ready-made "deepfake detector" models mostly don't work on our data.** On face swaps and inpainting they scored AUC 0.41–0.62, near coin-flip. If we had used them as-is, the live demo would have failed.

**Finding 2: a linear probe on face crops works.** Taking a model's embeddings of the *cropped face* and training a tiny classifier on top gave AUC around 0.90 (face swap 0.87).

**Finding 3 (Omkar's find, 26 Sep): the CommunityForensics model is excellent on generated content.** Omkar tested `buildborderless/CommunityForensics-DeepfakeDet-ViT` on 11 images. We then tested it on the full 650-image set:

| Detector | Face swap | Inpainting | Text-to-image | Real images wrongly flagged |
|---|---|---|---|---|
| Best ready-made model before | 0.58 | 0.62 | 0.93 | — |
| **Our face-crop probe** | **0.87** | 0.88 | 0.95 | 19% at the default cut-off |
| **Omkar's CommunityForensics** | 0.66 | **0.99** | **1.00** | **0.3%** |

**They cover each other's gaps.** CommunityForensics nails generated and inpainted images with almost no false alarms. The probe is best at face swaps. So S1 is both of them combined. The "combining helps" table will be one of the best slides in the demo.

**Finding 4: leakage trap, avoided.** In this dataset every manipulated image is exactly 512×512 while real ones vary in size, so a lazy model could learn "512×512 = manipulated" and look brilliant while being useless. We always crop the face and resize before the AI sees it, and we say so openly in the limitations. Judges respect this kind of honesty.

### 7.4 Team setup (GitHub repo)
- Repo: https://github.com/OjasPurohit/Unmask-deepEntra.ai
- `TEAM_SETUP.md`: one-line install for teammates, GitHub login steps, and the Android toolchain (JDK 21 + Android Studio) that Ojas and Palash install before the event.
- One briefing file per person, so each agent gets exactly the context its owner needs:
  - `context/OMKAR_AI_MODELS.md` — Omkar: face detection, S1 (`cf` + `probe`), occlusion heatmap, probe training, fusion, evaluation.
  - `context/YADNESH_BACKEND.md` — Yadnesh: ELA, FFT, noise, metadata, video/temporal, narrator, case store.
  - `context/FRONTEND_OJAS_PALASH.md` — Ojas and Palash: the exact data format plus a file-by-file ownership split so they never edit the same file.
  - `context/ANDROID_APP.md` — Ojas and Palash: the Capacitor Android app.
- `KICKOFF_PROMPTS.md`: one ready prompt per person to paste into Claude Code / Antigravity at 12:15, plus the integration, APK and polish prompts.
- `PLAN.md` §3.1 has a file → owner table covering every backend and frontend file.
- Omkar's branch `omkar/deepfake-detector` holds his model-comparison scripts and 11 test images.

---

## 8. Map of files
| File / folder | What it is |
|---|---|
| `EXPLAINED.md` | This document. |
| `PLAN.md` | Strategy, scoring map, architecture, timeline, demo script, risks. |
| `CLAUDE.md` | Technical rulebook for AI coding agents. Claude Code reads it automatically. |
| `AGENTS.md` | Tells Antigravity to read CLAUDE.md and PLAN.md. |
| `KICKOFF_PROMPTS.md` | Copy-paste prompts per person for 12:15, 1:45 and 2:45. |
| `TEAM_SETUP.md` | How teammates install tools and get the code. |
| `context/` | One briefing file per person: `OMKAR_AI_MODELS.md`, `YADNESH_BACKEND.md`, `FRONTEND_OJAS_PALASH.md`, `ANDROID_APP.md`. |
| `requirements.txt` | Python libraries list. |
| `scripts/setup.ps1` | One-command laptop setup. |
| `scripts/download_models.py` | Downloads all models. |
| `scripts/fetch_data.py` | Downloads the test data. |
| `scripts/benchmark_models.py` | Tests every ready-made model → `models/benchmark.json`. |
| `scripts/probe_experiment.py` | The face-crop probe experiment (Finding 2). |
| `models/`, `data/`, `.venv/` | Big local folders, **not on GitHub** (too large, third-party data). Share by pen drive. |
| `backend/`, `frontend/` | Don't exist yet. Built today from 12:15. |
| `frontend/android/` | The Capacitor Android project, generated by `npx cap add android` after 1:45. |

---

## 9. Who does what today
| Person | Role | Builds | Branch | Briefing |
|---|---|---|---|---|
| **Ojas** | Team lead / architect · frontend · Android | The 12:15 scaffold everyone else builds on (schemas, routes, pipeline with stubs, Vite skeleton), then the Evaluation page, Review queue, Settings and app shell, plus **the Android app**. Merges every branch at the checkpoints, runs integration testing, presents at 11:00 and leads the 4:00 demo. | `main` + `app` | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Palash** | Frontend · Android UI | The design system and shared components (which Ojas imports, so they come first), the **Analyze page**, the **Evidence Report page** (the demo centrepiece), and the mobile layout + camera flow the Android app uses. | `ui` | `context/FRONTEND_OJAS_PALASH.md` + `context/ANDROID_APP.md` |
| **Omkar** | AI models | Face detection and region masks (`face.py`), the S1 classifier with both sub-scores and the occlusion heatmap (`classifier.py`), probe training, fusion, the evaluation numbers, robustness and the failure gallery. | `models` | `context/OMKAR_AI_MODELS.md` |
| **Yadnesh** | Backend · ML | The four classic forensic signals (ELA, FFT, noise, metadata) and their calibration, the video pipeline (frames, blink rate, jitter), the AI narrator with its offline fallback, and the SQLite case store with the audit log. | `backend` | `context/YADNESH_BACKEND.md` |

Down a person: Omkar absorbs the noise and metadata signals, Ojas absorbs the video pipeline. Down two: drop noise, landmark jitter and the Android app.

**Git workflow:** each person works on their own branch and merges into `main` at the checkpoints (1:45, 2:45, 3:15). `PLAN.md` §3.1 lists every backend and frontend file with its owner, so two people never edit the same file. The one contract both halves depend on — `backend/schemas.py` and `frontend/src/types.ts` — is owned by Ojas alone.

---

## 10. Today's build plan
| Time | Milestone |
|---|---|
| 10:00–11:00 | Laptops set up, models load offline, `.env` has an API key. |
| 11:00 | Present the plan (deck). |
| 12:15–12:30 | Ojas pastes the MASTER prompt, creates the skeleton, pushes. Everyone pulls. |
| 12:30–1:45 | Everyone builds their part in parallel. The UI uses mock data. |
| **1:45 checkpoint** | An image goes end-to-end: upload → real report on screen. **If not, cut noise/metadata and keep going.** |
| 1:45–2:45 | Video, evaluation run, fusion, narrator, review queue. **The Android build starts here, and only if the checkpoint passed.** |
| 2:45–3:00 | APK rebuilt from the merged code, installed on the demo phone, one real analysis run end-to-end. **APK frozen at 3:00.** |
| 2:45–3:15 | Polish, prepare demo samples, **record a 90-second backup video of the demo** (including the phone beat). |
| **3:30** | Freeze. Rehearse the demo twice with a timer. |
| 4:00 | Demo. |

**Must-have (P0):** image upload, S1 with heatmap, ELA, FFT, regions, confidence band, report, evaluation page with real numbers.
**Should-have (P1):** video, noise, metadata, narrator, review queue, robustness.
**P1.5 — the Android APK:** started only after the 1:45 checkpoint passes, targeted for 3:00. It is a 30-second demo beat, not something anything else depends on; if it slips we show the web app in the phone's browser instead and lose nothing.
**Nice-to-have (P2):** live webcam check, content credentials, PDF export.

---

## 11. The 4-minute demo
1. **Hook (20 s):** "VSS admits students through applications and interviews. A face-swapped ID photo or an AI-generated profile defeats that in seconds."
2. **Real photo (35 s):** green, every signal calm. "We don't cry wolf."
3. **Face swap (55 s):** red, heatmap on the jawline, region chips, ELA and frequency panels, plain-English explanation, SHA-256.
4. **Video (35 s):** the timeline spikes; click the spike to see that frame's heatmap; low blink rate noted.
5. **Phone (30 s):** "a VSS admissions officer verifies an applicant photo from a phone" — open the Unmask app, upload or photograph, the band and heatmap appear on the phone, and the case lands in the review queue on the projector. Say the line: *the models never leave the verification machine; the phone is just a secure client.*
6. **Evaluation (45 s):** real numbers, false-positive rate, the "combining helps" table, and **a case we get wrong**: "this is exactly why the system never decides alone."
7. **Review (20 s):** the reviewer disagrees and adds a note; the audit log records it. Close with the guardrails and the next step: a pilot at the VSS admissions desk.

If the APK is not ready, beat 5 becomes the same web app opened in the phone's browser at the laptop's address. Same story, same 30 seconds.


---

## 12. Tough questions judges may ask, with answers
- **"Isn't this just a pretrained model?"** No. We benchmarked seven ready-made models and showed most fail on face swaps (AUC ~0.5). We built a face-crop probe that lifts face-swap detection to 0.87, combined it with the best generated-content model (0.99–1.00) and three classic forensic signals, and made all of it explainable.
- **"How accurate is it?"** Point to the evaluation page: accuracy, AUC and the false-positive rate on a held-out test set, broken down by manipulation type.
- **"What if it's wrong?"** It will be sometimes. That's why there's a failure gallery, confidence bands, an "inconclusive" zone, and a human who always decides.
- **"Could your model be cheating?"** We found a real leakage risk (image size) and removed it by cropping faces. Our limitations section also says the real and fake data come from different sources, and we checked our own selfies as out-of-distribution samples.
- **"Why use an LLM at all?"** Only to *explain* measured evidence in plain language for non-technical staff. It never sees the image and never decides.
- **"Does the AI run on the phone?"** No — and deliberately. The phone app is a **secure client**: it uploads the file to the verification machine over the local network and displays the result. The models (about 5 GB) and the case database stay on that one controlled machine. Three reasons: **privacy and governance** — applicant photos and the audit trail live in one place an institution can secure and inspect, not scattered across staff phones; **speed** — a GPU laptop returns a full multi-signal analysis in a couple of seconds where a phone would take far longer, if it could load the models at all; and **consistency** — everyone is scored by the same model version, so the evaluation numbers on our dashboard actually describe what the phone shows.
- **"Privacy?"** Everything runs locally on the verification machine. The images never leave it (the narrator gets numbers only), and the phone app talks to it over the local network, not the internet. SHA-256 gives integrity.
- **"What's next?"** A pilot at the VSS admissions desk, more training data (FaceForensics++, Celeb-DF), live interview liveness checks, and C2PA content-credential verification.

---

## 13. Checklist before 10:00 AM
- [ ] Laptops charged, chargers, extension board, phone hotspot, college ID.
- [ ] Teammates have the tools installed and the repo cloned (`TEAM_SETUP.md`).
- [ ] `models/` and `data/` copied to teammates (pen drive).
- [ ] Ojas and Palash have the Android toolchain working (JDK 21, Android Studio SDK, `adb devices` sees a phone, a throwaway Capacitor app built to an APK) — `TEAM_SETUP.md` §4.
- [ ] Demo phone charged, USB cable packed, "install unknown apps" allowed.
- [ ] `.env` has a Gemini or Claude API key, tested.
- [ ] 11:00 AM deck ready: problem → VSS impact → architecture → research findings table → evaluation plan → guardrails → build plan.
- [ ] Everyone has read their briefing file.
- [ ] Take 5–8 team selfies (with consent) for the out-of-distribution check.
