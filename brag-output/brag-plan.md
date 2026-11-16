# Infra Monitor — brag plan

**What it is:** Self-hosted monitoring for Linux servers. You enroll a server with one command, an ML model flags abnormal metrics, and an AI assistant explains what's going on.
**For:** People who run their own Linux boxes and don't want to read raw Grafana graphs at 3 AM.
**What sets it apart:** It goes past "your CPU is high". You get anomaly detection on six real features (`cpu_r, mem_u, disk_r, disk_w, eth1_fi, eth1_fo`), and Gemini explains the stored evidence, with the honest label *"AI advice — crash not confirmed"*.
**Hook:** A production CPU line spikes red at 03:07.
**Share caption:** One command to enroll a server, ML to spot the weird stuff, an AI to tell you what to check first.

## Angle
"The 3 AM problem, solved in three moves": **Enroll → Detect → Explain**. The video shows the product's own flow, rebuilt from the Flutter app's real copy, palette (`#071428` bg, `#2E6AFF` primary, `#6D5EFF` violet, `#EF4444` danger, `#20C997` success) and fonts (Inter + Roboto).

**Tone:** default (punchy, clean). **Format:** 1920×1080, 30 fps, 21 s.

## Music
120 BPM (beat = 0.5 s = 15 frames, bar = 2 s), A minor, Am–F–C–G. Kick, hats, soft snare, sub bass, pad, pluck arpeggio. Effects come from the same palette: filtered-noise risers into cuts, key-tuned UI ticks, and a low impact on the outro downbeat. Every cut lands on a beat.

## Storyboard
| # | Time | Scene | On screen |
|---|---|---|---|
| 1 | 0.0–3.0 | **Hook** | Full-width CPU chart for `web-prod-01 · production` draws in, spikes to 97% and turns red. Badge "ANOMALY · cpu_r". Line: **"03:07. CPU just hit 97%."** |
| 2 | 3.0–6.0 | **Reveal** | Infra Monitor wordmark + **"Linux server monitoring that explains itself."** |
| 3 | 6.0–10.0 | **Enroll** | Real *Add server* panel: "Enroll a monitored server", server name typed in, Production, click **Generate install command**, then "Enrollment command ready", command block, **Copy command**, toast "Install command copied." Caption: **"Add a server in one command."** |
| 4 | 10.0–14.0 | **Detect** | Overview: FLEET STATUS, OPEN CRITICAL, cpu_r chart with an anomaly band, and the six feature chips with `cpu_r`/`disk_w` lit. An incident card slides in. Caption: **"ML flags what's abnormal."** |
| 5 | 14.0–18.0 | **Explain** | AI assistant: "AI advice — crash not confirmed", the real SUGGESTED PROMPTS, a click on "What should I check first?", and a streamed checklist. Caption: **"Then ask the AI why."** |
| 6 | 18.0–21.0 | **Outro** | Infra Monitor · **"Enroll. Detect. Explain."** · `docker compose up` |

Transitions: old content leaves first, then new content enters (dip through the background). No crossfades between busy layouts.

## Fictional stand-ins
The server name `web-prod-01`, host `infra.example.com`, metric values, counts, incident ID `INC-1042` and the assistant's answer text are illustrative. The real enrollment token is masked (`••••`). No real users, hosts or keys appear.
