# 100 Awesome Brand Demos

Copy-and-paste briefs for demoing, testing, or seeding Brand Maker. Every entry is
fictional and safe to generate.

## How to use one

1. Start the app (`uv run brand-maker`) and open `http://127.0.0.1:8000`.
2. Paste the **name** into *Brand or working name*, paste the fenced block into
   *What do you already know?*, then click **Create workspace**.
3. In the workshop, click **Generate or refresh complete draft**, then paste the
   **Logo** line into *Extra instructions* and click **Generate logo**.

Prefer the API? Same content, one call:

```bash
curl -X POST http://127.0.0.1:8000/api/brands \
  -H 'Content-Type: application/json' \
  -d '{"brand_name":"Third Rise","brand_context":"Objective: ...\nAudience: ..."}'
```

The suggested *entry path* and *AI mode* on each demo are just what makes the demo
read best; any combination works.

---

## Food & Drink

### 1. Kettle & Coil
`Kettle & Coil` — named concept · copilot

```text
Objective: Sell precision pour-over kettles and brewing gear to people who already own a grinder.
Audience: Home coffee obsessives, 25-45, who watch brewing videos and weigh their beans.
Edge: Every product ships with the exact recipe card it was designed around.
Tone: Precise, unpretentious, quietly nerdy. No latte-art lifestyle posturing.
```
Logo: `Minimal line mark of a gooseneck spout forming a spiral, monochrome, legible at 16px`

### 2. Brackish
`Brackish` — existing project · advisor

```text
Objective: Grow a coastal oyster farm's direct-to-door subscription beyond the local farmers market.
Audience: Home cooks in inland cities who have never shucked an oyster and are slightly intimidated.
Edge: Each box names the exact tidal lease the oysters grew on, with a shucking lesson card.
Tone: Salt-air plain-spoken. Working waterfront, not white tablecloth.
```
Logo: `Rough-edged oyster shell in negative space, two-tone slate and cream`

### 3. Third Rise
`Third Rise` — raw idea · autonomous strategist

```text
Objective: Open a sourdough bakery that sells out by 11am and is fine with that.
Audience: Neighborhood regulars within a fifteen-minute walk, plus weekend visitors.
Edge: One bread, three pastries, no menu expansion ever. Everything is same-day.
Tone: Warm, stubborn, a little funny about the rules it refuses to break.
```
Logo: `Three ascending arcs suggesting dough rising, hand-drawn weight, single ink color`

### 4. Nomad Noodle
`Nomad Noodle` — named concept · copilot

```text
Objective: Turn a regional ramen pop-up into a bookable residency that tours other cities' kitchens.
Audience: Food-scene followers who track chef collaborations and will queue in the rain.
Edge: The broth changes with the host city's local produce; the noodle never does.
Tone: Energetic, itinerant, respectful of the tradition it is bending.
```
Logo: `A noodle strand drawn as a travel route with a single pin, bold and flat`

### 5. Pepper Ledger
`Pepper Ledger` — raw idea · copilot

```text
Objective: Launch a hot sauce subscription organized by heat and use, not by novelty.
Audience: People who own six sauces and use two, and want to stop guessing.
Edge: Every bottle is labeled with Scoville, acidity, and the three dishes it was built for.
Tone: Deadpan, methodical, allergic to skull-and-flames macho packaging.
```
Logo: `A pepper silhouette ruled like a ledger line, restrained two-color palette`

### 6. Copper Hollow
`Copper Hollow` — named concept · advisor

```text
Objective: Establish a small-batch bourbon distillery's identity before its first four-year release.
Audience: Whiskey buyers who read mash bills and distrust invented heritage stories.
Edge: Publishes every barrel's real numbers, including the batches it decided not to bottle.
Tone: Patient, factual, confident without folklore.
```
Logo: `Copper still curve abstracted into a hollow valley shape, warm metallic accent`

### 7. Rootline
`Rootline` — raw idea · autonomous strategist

```text
Objective: Sell frozen meals built around root vegetables that taste like they were never frozen.
Audience: Weeknight cooks who feel guilty about the freezer aisle but keep going back.
Edge: Root-forward recipes freeze better than leafy ones; the whole menu is built on that fact.
Tone: Practical, food-first, honestly unglamorous about convenience.
```
Logo: `Taproot descending into a single clean baseline, flat vegetal green`

### 8. Milkhouse Nine
`Milkhouse Nine` — existing project · advisor

```text
Objective: Move a regenerative dairy from commodity milk sales into its own creamery brand.
Audience: Grocery shoppers who read labels and regional chefs sourcing within 100 miles.
Edge: Nine cows, named, with grazing records anyone can look up.
Tone: Unhurried, agricultural, allergic to greenwashing language.
```
Logo: `Numeral nine formed from a milk pour, cream on deep field green`

### 9. Saffron Freight
`Saffron Freight` — named concept · copilot

```text
Objective: Import Persian pantry staples direct to home cooks outside major diaspora cities.
Audience: Second-generation cooks recreating family dishes and curious cooks who bought one cookbook.
Edge: Ships the specific grade and harvest a recipe actually calls for, not a generic tin.
Tone: Generous, teacherly, proud without being precious.
```
Logo: `Saffron thread bent into a shipping route arc, crimson on ivory`

### 10. Half Past Honey
`Half Past Honey` — raw idea · copilot

```text
Objective: Sell honey from rooftop hives across one city, bottled by neighborhood.
Audience: Locals who will pay more for something that tastes like six blocks from their house.
Edge: Same bees, wildly different flavor by district; the label is a map.
Tone: Playful, hyper-local, lightly obsessed with terroir.
```
Logo: `Hexagon clock face at half past, amber and charcoal`

---

## Software & Developer Tools

### 11. Loomlock
`Loomlock` — named concept · copilot

```text
Objective: Ship a dependency drift monitor that tells teams which upgrades are actually urgent.
Audience: Platform engineers drowning in automated bump PRs nobody reviews.
Edge: Ranks drift by reachable code paths, not by semver distance.
Tone: Calm, specific, hostile to alert fatigue.
```
Logo: `Interlocking thread and shackle forming a single mark, monochrome, terminal-friendly`

### 12. Quietport
`Quietport` — raw idea · advisor

```text
Objective: Offer a self-hosted status page that stays up when the product it reports on does not.
Audience: Small SaaS teams who cannot justify enterprise incident tooling.
Edge: Runs on a separate provider by default and refuses to share any dependency with your stack.
Tone: Dry, reassuring, deeply unexcitable.
```
Logo: `Harbor light beam rendered as a flat semicircle, two-tone slate`

### 13. Runegraph
`Runegraph` — named concept · autonomous strategist

```text
Objective: Give background jobs and queues the observability that HTTP requests already have.
Audience: Backend engineers debugging a worker that silently stopped six hours ago.
Edge: Traces jobs across retries and re-enqueues as one continuous lifecycle.
Tone: Technical, confident, no marketing abstraction over the actual mechanism.
```
Logo: `Directed graph node trail forming a rune-like glyph, single accent color`

### 14. Slate & Socket
`Slate & Socket` — raw idea · copilot

```text
Objective: Build hardware-in-the-loop CI for teams shipping firmware on real boards.
Audience: Embedded developers who currently test by walking to a bench and plugging in a cable.
Edge: Physical device farm with per-run power cycling and captured serial logs.
Tone: Bench-side practical, respectful of how messy real hardware is.
```
Logo: `Plug prong and slate rectangle locked together, industrial and flat`

### 15. Ferrylight
`Ferrylight` — named concept · copilot

```text
Objective: Make database migrations safe to run during business hours.
Audience: Teams with one production database and no window to take it down.
Edge: Simulates each migration against a shadow copy under real traffic before it commits.
Tone: Steady, safety-first, unwilling to promise magic.
```
Logo: `Beacon over two parallel rails, warm signal color on dark`

### 16. Hushline
`Hushline` — raw idea · advisor

```text
Objective: Cut on-call paging volume without hiding real incidents.
Audience: Engineering leads whose rotation is burning people out on false pages.
Edge: Groups correlated alerts into one incident and shows exactly what it suppressed.
Tone: Empathetic about 3am, rigorous about not dropping signal.
```
Logo: `Waveform flattening into a single quiet line, muted blue`

### 17. Papertrace
`Papertrace` — named concept · copilot

```text
Objective: Sell drop-in audit logging that satisfies compliance reviewers on the first pass.
Audience: Startups hitting their first SOC 2 or HIPAA requirement with no security hire.
Edge: Append-only, hash-chained, and exportable in the exact format auditors ask for.
Tone: Precise, procedural, never casual about integrity claims.
```
Logo: `Paper sheet corner with an embedded chain link, ink-on-white`

### 18. Bramble
`Bramble` — raw idea · autonomous strategist

```text
Objective: Ship a monorepo task runner that new contributors understand on day one.
Audience: Teams whose build system needs a designated expert to change safely.
Edge: One config file, explicit dependency edges, and a plain-English explain command.
Tone: Direct, anti-magic, willing to be boring.
```
Logo: `Branching thorn line forming a simple dependency tree, deep green on bone`

### 19. Northfield API
`Northfield API` — named concept · advisor

```text
Objective: Provide address normalization and geocoding for logistics teams in rural regions.
Audience: Developers whose deliveries fail because the address is a mile marker and a mailbox.
Edge: Handles unaddressed and informally addressed locations that mainstream geocoders drop.
Tone: Grounded, unglamorous, proud of the ugly edge cases.
```
Logo: `Compass needle over a field grid, flat two-color`

### 20. Tinderbox Labs
`Tinderbox Labs` — raw idea · copilot

```text
Objective: Bring chaos engineering to teams too small for a resilience department.
Audience: Ten-person startups who have never tested what happens when the database fails over.
Edge: Preset failure drills with a blast radius you set before anything runs.
Tone: Serious about safety, cheerfully blunt about how fragile most systems are.
```
Logo: `Struck match abstracted into a contained box outline, ember accent`

---

## Health & Wellness

### 21. Steady State
`Steady State` — named concept · copilot

```text
Objective: Coach adults out of chronic insomnia using CBT-I instead of supplements.
Audience: People who have tried every sleep gadget and still wake at 3am.
Edge: Behavioral protocol delivered by real clinicians, with no product to upsell.
Tone: Clinical but kind. Never mystical, never a wellness influencer.
```
Logo: `Flat horizon line with a single gentle sine settling into it, indigo`

### 22. Marrow & Moss
`Marrow & Moss` — raw idea · advisor

```text
Objective: Run an herbal apothecary that is honest about what evidence exists and what does not.
Audience: Customers who want plant-based remedies but are tired of unverifiable claims.
Edge: Every product page states the evidence level plainly, including "traditional use only."
Tone: Earthy and warm, with a scientist's discipline about claims.
```
Logo: `Mortar and pestle silhouette with moss texture edge, forest and clay`

### 23. Clearwater Counsel
`Clearwater Counsel` — named concept · advisor

```text
Objective: Deliver teletherapy built specifically for first responders and their families.
Audience: Firefighters, paramedics, and dispatchers who will not walk into a general clinic.
Edge: Every clinician is trained in shift work, critical incident stress, and department culture.
Tone: Steady, confidential, plainly respectful of the job.
```
Logo: `Still water ripple inside a shield outline, calm blue-grey`

### 24. Hinge & Hollow
`Hinge & Hollow` — raw idea · copilot

```text
Objective: Sell mobility training for people who sit ten hours a day and hurt by Thursday.
Audience: Desk workers in their thirties and forties who are not going to become gym people.
Edge: Ten-minute sessions designed to be done in work clothes next to a desk.
Tone: Unembarrassing, practical, zero fitness-industry shame.
```
Logo: `Hinge joint abstracted into two arcs meeting, warm neutral palette`

### 25. Second Wind Clinic
`Second Wind Clinic` — existing project · advisor

```text
Objective: Reposition a pulmonary rehab practice around long-term function, not discharge dates.
Audience: Adults recovering from COPD flares, long COVID, or major lung surgery.
Edge: Home-based programs with equipment loans and a therapist who calls, not a portal message.
Tone: Encouraging without minimizing. Progress measured in stairs, not slogans.
```
Logo: `Two overlapping breath curves forming a lung shape, teal and white`

### 26. Lumen Dental Studio
`Lumen Dental Studio` — named concept · copilot

```text
Objective: Open a dental practice for adults with dental anxiety severe enough to skip a decade.
Audience: People who have avoided a cleaning since college and dread being lectured.
Edge: No-shame intake, published prices, and a stop signal the patient controls.
Tone: Gentle, transparent, completely free of judgment.
```
Logo: `Soft light aperture forming a tooth silhouette in negative space, pale gold`

### 27. Fallow Season
`Fallow Season` — raw idea · autonomous strategist

```text
Objective: Build a perimenopause care service that takes symptoms seriously the first time.
Audience: Women 40-55 who have been told their labs are normal and to try yoga.
Edge: Structured symptom tracking that becomes a clinical record their prescriber will accept.
Tone: Direct, well-informed, quietly furious on the patient's behalf.
```
Logo: `Bare field horizon under a low sun, muted ochre and plum`

### 28. Trailhead Nutrition
`Trailhead Nutrition` — named concept · copilot

```text
Objective: Grow a sports dietitian practice serving amateur endurance athletes.
Audience: Marathon and gravel racers taking fueling advice from forum threads.
Edge: Race-day fueling plans tested in training blocks, adjusted after every event.
Tone: Coachy, evidence-based, no supplement affiliate energy.
```
Logo: `Trail marker chevron with a fork mark, forest green on sand`

### 29. Quiet Hours
`Quiet Hours` — raw idea · advisor

```text
Objective: Run a fitness studio designed for sensory-sensitive and neurodivergent members.
Audience: Adults who want to exercise but cannot tolerate mirrors, music, and crowds.
Edge: Low-light, low-noise sessions with capped attendance and predictable structure.
Tone: Calm, literal, specific about exactly what the room will be like.
```
Logo: `Sound wave reduced to a single flat dash inside a rounded square, soft sage`

### 30. Patch Kit
`Patch Kit` — named concept · copilot

```text
Objective: Sell first-aid kits organized for panicked parents rather than for wilderness experts.
Audience: New parents who own a kit and cannot find anything in it during an actual incident.
Edge: Color-coded modules by injury type with a one-page card on top of each.
Tone: Reassuring, fast, no gore and no fear-selling.
```
Logo: `Bandage cross made of two rounded modules, bright signal red and cream`

---

## Finance & Professional Services

### 31. Ledgerbird
`Ledgerbird` — named concept · copilot

```text
Objective: Do bookkeeping for freelancers who missed two quarters and are scared to ask.
Audience: Designers, contractors, and consultants earning 60-200k with shoebox records.
Edge: Catch-up cleanup is the entry product, not a penalty add-on.
Tone: Nonjudgmental, plain-language, allergic to accountant jargon.
```
Logo: `Bird silhouette formed from two ledger rules, ink blue on paper white`

### 32. Anchor Point Wealth
`Anchor Point Wealth` — named concept · advisor

```text
Objective: Build a fee-only advisory for people who inherited money and feel unqualified.
Audience: First-time inheritors, 30-55, who fear making an irreversible mistake.
Edge: Flat fee, no product sales, and a written decision log the client keeps.
Tone: Sober, unhurried, protective of the client's autonomy.
```
Logo: `Anchor reduced to a single point-and-arc mark, deep navy`

### 33. Rampart Tax
`Rampart Tax` — raw idea · advisor

```text
Objective: Prepare US expat tax returns without the annual panic and surprise fees.
Audience: Americans living abroad who dread FBAR, FEIE, and mismatched tax years.
Edge: Fixed quoted price before any work starts, and every form explained in one paragraph.
Tone: Steady, jurisdictionally precise, never alarmist.
```
Logo: `Fortified wall notch pattern forming a shield, slate and brass`

### 34. Coop Capital
`Coop Capital` — named concept · autonomous strategist

```text
Objective: Lend to worker cooperatives that traditional underwriting scores badly.
Audience: Cooperative bakeries, garages, and home care agencies with no single owner to guarantee.
Edge: Underwrites collective governance and cash flow instead of a personal guarantee.
Tone: Mission-clear, financially rigorous, never charity-flavored.
```
Logo: `Interlocked circles forming a supportive ring, warm ochre and ink`

### 35. Two Rivers Title
`Two Rivers Title` — existing project · advisor

```text
Objective: Modernize a regional title company that still closes with paper and fax.
Audience: Realtors and buyers in a two-county area who want a closing date that holds.
Edge: Local title expertise with digital closings and a published turnaround clock.
Tone: Trustworthy, procedural, proud of a hundred-year archive.
```
Logo: `Two converging river curves forming a document fold, muted blue-green`

### 36. Signal Counsel
`Signal Counsel` — named concept · copilot

```text
Objective: Provide legal operations for seed-stage startups before they can hire counsel.
Audience: Founders signing contracts they do not fully understand at 11pm.
Edge: Subscription review with a 24-hour turn and a plain-English risk verdict on top.
Tone: Fast, decisive, comfortable saying "this is fine, sign it."
```
Logo: `Signal bars ascending into a gavel-free abstract mark, monochrome`

### 37. Keel Risk
`Keel Risk` — raw idea · advisor

```text
Objective: Broker marine and inland waterway insurance for small commercial operators.
Audience: Tug, barge, and charter owners with one to five vessels and no risk manager.
Edge: Coverage explained against real claim scenarios from the same waterways.
Tone: Working-boat direct, technically fluent, no corporate insurance fog.
```
Logo: `Keel line cutting a waterline, deep hull blue and rope tan`

### 38. Payload Payroll
`Payload Payroll` — named concept · copilot

```text
Objective: Run payroll for construction crews with prevailing wage and multi-state jobs.
Audience: Contractors with 10-80 field employees and a bookkeeper doing this in spreadsheets.
Edge: Certified payroll reports generated automatically per job site and jurisdiction.
Tone: Job-site practical, compliance-literate, unimpressed by software buzzwords.
```
Logo: `Payload container shape with a stacked pay line, safety orange and graphite`

### 39. Almanac Advisors
`Almanac Advisors` — named concept · advisor

```text
Objective: Guide farm families through succession before the transfer becomes a crisis.
Audience: Owners over 60 with land, equipment, and adult children with different plans.
Edge: Facilitates the family conversation first, then builds the legal and tax structure.
Tone: Patient, generational, respectful of what the land means.
```
Logo: `Almanac page corner with a seasonal wheel, harvest gold on dark green`

### 40. Bellwether Audit
`Bellwether Audit` — raw idea · advisor

```text
Objective: Deliver financial audits for nonprofits under $10M that big firms deprioritize.
Audience: Executive directors facing a grant-mandated audit with a two-person finance team.
Edge: Fixed-scope audits on a published calendar, with prep coaching included.
Tone: Reliable, unintimidating, clear about what auditors can and cannot do.
```
Logo: `Bell silhouette formed from a rising bar chart, muted brass`

---

## Education & Learning

### 41. Chalk & Compass
`Chalk & Compass` — named concept · copilot

```text
Objective: Publish a homeschool math curriculum for parents who are not math people.
Audience: Homeschooling parents who can teach reading confidently and dread fractions.
Edge: Every lesson includes a script for the parent, not just work for the child.
Tone: Reassuring, rigorous, never condescending to either the parent or the kid.
```
Logo: `Compass arc drawn in chalk texture, slate board and white`

### 42. Verbatim
`Verbatim` — raw idea · autonomous strategist

```text
Objective: Match language learners with tutors by accent, register, and actual use case.
Audience: Adults who studied a language for years and still freeze on a phone call.
Edge: Sessions are built around the learner's real upcoming conversation, not a textbook unit.
Tone: Confidence-building, practical, unbothered by grammatical perfection.
```
Logo: `Quotation mark pair forming a speech bridge, two-tone`

### 43. Foundry Nights
`Foundry Nights` — named concept · copilot

```text
Objective: Run evening welding and fabrication classes for adults changing careers.
Audience: Warehouse and retail workers who want a trade but cannot quit for a day program.
Edge: Six-week certifications with employer partners who interview every graduating cohort.
Tone: No-nonsense, encouraging, respectful of people who work all day first.
```
Logo: `Spark arc over an anvil edge, ember orange on iron grey`

### 44. Kite String
`Kite String` — raw idea · advisor

```text
Objective: Grow an early childhood literacy nonprofit's book distribution across a county.
Audience: Donors, pediatric clinics, and caregivers of children under five.
Edge: Books delivered through well-child visits, so they reach families who never visit a library.
Tone: Hopeful, concrete about outcomes, never pitying the families it serves.
```
Logo: `Kite string curving into an open book spine, sky blue and coral`

### 45. Second Draft
`Second Draft` — named concept · copilot

```text
Objective: Teach writing workshops for scientists who need their papers to be readable.
Audience: Postdocs and PIs whose reviewers keep saying the manuscript is hard to follow.
Edge: Works on the participant's actual in-progress manuscript, not sample exercises.
Tone: Peer-to-peer, rigorous, never treating scientists as bad writers.
```
Logo: `Manuscript page with one clean revision stroke, ink on cream`

### 46. Cipher Camp
`Cipher Camp` — raw idea · copilot

```text
Objective: Run summer cybersecurity camps for teens with no prior programming background.
Audience: Parents of 13-17 year olds and school counselors looking for real career exposure.
Edge: Capture-the-flag challenges built on a fictional town's infrastructure, plus an ethics track.
Tone: Exciting, hands-on, explicit that skills come with responsibility.
```
Logo: `Rotating cipher wheel simplified to two nested rings, electric green on black`

### 47. Groundwork Institute
`Groundwork Institute` — named concept · advisor

```text
Objective: Launch a fellowship placing early-career people into local government policy roles.
Audience: Recent graduates who want public service and cannot afford an unpaid year.
Edge: Paid placements in city and county offices, with a cohort that stays connected after.
Tone: Civic, serious, unshowy about impact claims.
```
Logo: `Foundation line with three rising columns, civic stone and deep blue`

### 48. Playbook U
`Playbook U` — raw idea · copilot

```text
Objective: Certify volunteer youth sports coaches in safety, development, and communication.
Audience: Parent coaches handed a roster and a bag of balls with no training.
Edge: Four hours, sport-agnostic, with printable practice plans by age group.
Tone: Practical, kid-first, gently corrective about win-at-all-costs habits.
```
Logo: `Whistle silhouette drawn from playbook arrows, court blue and white`

### 49. Ivyless
`Ivyless` — named concept · autonomous strategist

```text
Objective: Provide test prep and application coaching for first-generation college applicants.
Audience: High school juniors whose families have never navigated an admissions process.
Edge: Coaches the whole process, including financial aid forms, not just the test score.
Tone: Demystifying, confident, openly skeptical of prestige obsession.
```
Logo: `Leaf shape cut from an open gate, bright green and deep plum`

### 50. Blueprint Bench
`Blueprint Bench` — raw idea · copilot

```text
Objective: Teach CAD and GD&T to working machinists who learned on manual equipment.
Audience: Shop floor machinists over 40 whose employers are converting to CNC.
Edge: Taught in shop language with real part drawings, not software feature tours.
Tone: Respectful of existing expertise, patient with new software, zero condescension.
```
Logo: `Caliper over a blueprint grid corner, blueprint blue and white`

---

## Media & Entertainment

### 51. Static & Stone
`Static & Stone` — named concept · copilot

```text
Objective: Build an independent documentary studio around long-form regional stories.
Audience: Festival programmers, streaming acquisitions, and a direct patron audience.
Edge: Films are made where the crew lives, over years, with the subjects' ongoing consent.
Tone: Observational, unsentimental, ethically explicit about its methods.
```
Logo: `Television static band across a carved stone slab, high contrast monochrome`

### 52. The Long Tally
`The Long Tally` — raw idea · advisor

```text
Objective: Sustain investigative local news in a mid-sized city after the daily paper closed.
Audience: Residents who still want to know how their school board and sheriff spend money.
Edge: Every story publishes its documents and its cost to produce.
Tone: Rigorous, accountable, civic without being self-congratulatory.
```
Logo: `Tally marks accumulating into a column rule, newsprint black on off-white`

### 53. Backchannel FM
`Backchannel FM` — named concept · copilot

```text
Objective: Launch a podcast network made by and for skilled trades workers.
Audience: Electricians, HVAC techs, and plumbers listening in the van between calls.
Edge: Hosts still work the trade; episodes run the length of an average drive.
Tone: Funny, profane-adjacent, technically credible, never white-collar tourism.
```
Logo: `Radio wave arcs emerging from a conduit bend, safety yellow on charcoal`

### 54. Pixel Reef
`Pixel Reef` — raw idea · autonomous strategist

```text
Objective: Establish a small studio making cozy games with no fail states.
Audience: Players who want forty relaxing hours and bounce off difficulty-as-content.
Edge: Every game ships complete, with no live service, battle pass, or roadmap.
Tone: Warm, unhurried, quietly opinionated about what games owe players.
```
Logo: `Coral branch built from soft pixel blocks, teal and coral gradient-free palette`

### 55. Marginalia Press
`Marginalia Press` — named concept · advisor

```text
Objective: Run a small press publishing translated fiction from under-represented languages.
Audience: Literary readers, translators, and independent bookstores.
Edge: Translators are named on the cover and paid royalties, not flat fees.
Tone: Bookish, principled, internationalist without exoticism.
```
Logo: `Marginal annotation bracket beside a text block, ink and vermilion`

### 56. Rowdy Bell
`Rowdy Bell` — raw idea · copilot

```text
Objective: Grow a neighborhood improv theater into a training program with a house team.
Audience: Adults who want a low-stakes creative outlet and local audiences on a Friday.
Edge: Classes explicitly designed for people who are not trying to become comedians.
Tone: Loud, welcoming, gently mocking of improv-scene self-seriousness.
```
Logo: `Bell shape formed from an open laughing mouth curve, hot pink and black`

### 57. Bellhouse Sessions
`Bellhouse Sessions` — named concept · copilot

```text
Objective: Turn a live music venue's recordings into a released catalog and revenue stream.
Audience: Fans who were there, plus listeners who follow small-room live recordings.
Edge: Multi-track captures of every show, released only with the artist's split agreed first.
Tone: Room-sound honest, artist-first, allergic to exploitative catalog deals.
```
Logo: `Bell curve of a room reverb tail over a stage line, warm amber on black`

### 58. Nightcart Cinema
`Nightcart Cinema` — raw idea · copilot

```text
Objective: Operate a mobile outdoor cinema that appears in parking lots and parks.
Audience: Neighborhoods without a theater, plus event organizers looking for a summer draw.
Edge: Programming is voted on locally the week before each screening.
Tone: Festive, portable, a little scrappy on purpose.
```
Logo: `Projector beam widening from a cart wheel, moonlight silver on night blue`

### 59. Skiff
`Skiff` — named concept · autonomous strategist

```text
Objective: Produce short-form audio drama, fifteen minutes per episode, fully scored.
Audience: Commuters and dog-walkers who want fiction but not a twelve-hour audiobook.
Edge: Every season is written to be finished; no cliffhanger without a resolution shipped.
Tone: Cinematic, tight, respectful of a listener's limited window.
```
Logo: `Small boat hull formed from a waveform, single sail as a play triangle`

### 60. Meeple & Manor
`Meeple & Manor` — raw idea · copilot

```text
Objective: Open a board game cafe that teaches games instead of just shelving them.
Audience: Groups who own three games, always play the same one, and want out of that rut.
Edge: Staff game guides teach any title in ten minutes; the library is curated, not exhaustive.
Tone: Hospitable, enthusiastic, never gatekeeping about hobby depth.
```
Logo: `Meeple silhouette inside a manor gable, mustard and deep teal`

---

## Local & Hospitality

### 61. Wandering Hearth
`Wandering Hearth` — named concept · advisor

```text
Objective: Position a six-room rural inn as a destination rather than a highway stopover.
Audience: City couples looking for a two-night reset within a three-hour drive.
Edge: One shared dinner every night, cooked from what the neighboring farms sent that day.
Tone: Hospitable, rooted, quietly luxurious without resort language.
```
Logo: `Hearth arch with a small path leading in, warm ember and slate`

### 62. Two Dogs Garage
`Two Dogs Garage` — existing project · copilot

```text
Objective: Grow an independent auto shop competing against dealership service departments.
Audience: Drivers of 5-15 year old cars who assume every shop will upsell them.
Edge: Photo-documented estimates, and it will tell you when a repair is not worth doing.
Tone: Straight-talking, unpretentious, funny about the shop dogs.
```
Logo: `Two dog silhouettes forming a wrench outline, garage blue and cream`

### 63. Bright Broom
`Bright Broom` — raw idea · copilot

```text
Objective: Build a residential cleaning service using only fragrance-free, low-tox products.
Audience: Households with asthma, chemical sensitivity, infants, or cats.
Edge: Publishes every product and ingredient used, and brings its own filtered water.
Tone: Clear, allergen-literate, never fear-mongering about chemicals.
```
Logo: `Broom bristle fan drawn as a light burst, mint and white`

### 64. Sawhorse
`Sawhorse` — named concept · advisor

```text
Objective: Keep a neighborhood hardware store relevant against big-box and same-day delivery.
Audience: Homeowners and renters doing small repairs who need advice more than inventory.
Edge: Free five-minute repair consults, and it will sell you the 60-cent part.
Tone: Neighborly, knowledgeable, dry about DIY overconfidence.
```
Logo: `Sawhorse frame as a simple A-form, workshop red and weathered wood`

### 65. Ferry Street Flowers
`Ferry Street Flowers` — named concept · copilot

```text
Objective: Move a florist from wire-service orders to local subscriptions and events.
Audience: Neighborhood regulars, plus couples planning small weddings under 60 guests.
Edge: Seasonal-only sourcing within the region; no imported roses in January.
Tone: Warm, seasonal, honest that you cannot have peonies in December.
```
Logo: `Single stem bending like a street sign post, dusty rose and sage`

### 66. Latchkey
`Latchkey` — raw idea · copilot

```text
Objective: Offer property management for landlords with one to four units.
Audience: Accidental landlords who inherited a duplex and hate the 2am phone calls.
Edge: Flat monthly fee with maintenance handled by a vetted local crew, no markup games.
Tone: Calm, boundaried, protective of both landlord and tenant relationships.
```
Logo: `Key bit forming a small house roofline, brass on deep grey`

### 67. Muddy Paws Retreat
`Muddy Paws Retreat` — named concept · copilot

```text
Objective: Run rural dog boarding for owners who feel guilty about kennels.
Audience: Dog owners traveling 3-10 days who want photos and a real yard.
Edge: Small groups matched by play style, with two daily updates from the handler.
Tone: Affectionate, competent, honest about which dogs are not a fit.
```
Logo: `Paw print with one clean grass blade, muddy brown and meadow green`

### 68. Cast Iron Catering
`Cast Iron Catering` — raw idea · advisor

```text
Objective: Build a catering business around one-pan regional cooking for 20-150 guests.
Audience: Backyard weddings, memorials, and company gatherings that want real food.
Edge: Cooks on site over fire; the menu is short and seasonal by design.
Tone: Generous, unfussy, proud of feeding people well without a banquet hall.
```
Logo: `Skillet circle with a single flame notch, black iron and ember`

### 69. Foghorn Charters
`Foghorn Charters` — named concept · copilot

```text
Objective: Fill weekday slots on a small fishing charter fleet in the shoulder season.
Audience: Beginners and families, not just serious anglers chasing trophy fish.
Edge: Beginner trips with gear, licenses, and cleaning included, no experience assumed.
Tone: Weatherbeaten, friendly, straight about seasickness and what you might not catch.
```
Logo: `Foghorn bell shape emitting three flat sound arcs, harbor red and fog grey`

### 70. Rekindle Salvage
`Rekindle Salvage` — raw idea · autonomous strategist

```text
Objective: Sell architectural salvage from demolitions to renovators and makers.
Audience: Old-house owners hunting period-correct doors, hardware, and heart pine.
Edge: Every piece is tagged with the building and year it came out of.
Tone: Preservationist, hands-on, unsentimental about what cannot be saved.
```
Logo: `Doorknob and beam joint forming a single mark, reclaimed wood and iron`

---

## Sustainability & Outdoors

### 71. Peat & Pine
`Peat & Pine` — named concept · advisor

```text
Objective: Fund and run native reforestation on retired farmland in one watershed.
Audience: Individual donors, landowners considering enrollment, and corporate offset buyers.
Edge: Publishes survival rates per planting year, including the bad ones.
Tone: Ecological, long-horizon, hostile to offset math that does not survive scrutiny.
```
Logo: `Pine silhouette rooted in a peat layer cross-section, deep green on umber`

### 72. Currentwise
`Currentwise` — raw idea · copilot

```text
Objective: Sell home energy audits that end in a ranked, priced action list.
Audience: Homeowners with a $400 winter bill and no idea what to fix first.
Edge: Every recommendation shows payback period and available local rebates.
Tone: Numeric, practical, uninterested in selling you a heat pump you do not need.
```
Logo: `Current arrow bending through a house outline, electric blue and warm grey`

### 73. Tidemark Gear
`Tidemark Gear` — named concept · copilot

```text
Objective: Sell plastic-free surf and swim accessories that survive real saltwater use.
Audience: Surfers who care about ocean plastic and have been burned by flimsy eco gear.
Edge: Natural rubber, waxed canvas, and a repair service instead of a replacement upsell.
Tone: Coastal, durable, allergic to eco-virtue marketing.
```
Logo: `Tide line mark across a simple wave, sea foam and driftwood`

### 74. Loamworks
`Loamworks` — raw idea · autonomous strategist

```text
Objective: Operate neighborhood-scale composting with curbside pickup and finished soil return.
Audience: Households and small restaurants in cities with no municipal organics program.
Edge: Subscribers get finished compost back each spring, weighed and labeled.
Tone: Cheerful about a gross subject, operationally precise, community-scaled.
```
Logo: `Soil layer bands forming a bucket profile, rich brown and sprout green`

### 75. Second Ascent Gear
`Second Ascent Gear` — named concept · copilot

```text
Objective: Build a trusted marketplace for used climbing and mountaineering gear.
Audience: Climbers who want affordable gear but will not gamble on unknown soft goods.
Edge: Every load-bearing item is inspected and dated; retired gear is destroyed, not resold.
Tone: Safety-obsessed, gear-nerd credible, blunt about what should never be bought used.
```
Logo: `Carabiner gate forming an upward arrow, granite grey and alpine orange`

### 76. Rainbarrel Co.
`Rainbarrel Co.` — raw idea · copilot

```text
Objective: Sell and install residential rainwater capture in drought-restricted regions.
Audience: Homeowners with dying gardens and watering-day limits.
Edge: Sized to the actual roof and rainfall data for the address, with permits handled.
Tone: Regionally specific, water-literate, unpanicked about drought reality.
```
Logo: `Barrel stave curve catching one drop, rain blue and cedar`

### 77. Wolfpine Trails
`Wolfpine Trails` — named concept · advisor

```text
Objective: Grow a trail-building cooperative contracting with parks and land trusts.
Audience: Land managers, municipal parks departments, and mountain bike alliances.
Edge: Builds sustainable grade-reversal trail that needs less maintenance in five years.
Tone: Dirt-under-fingernails technical, ecological, proud of unglamorous drainage work.
```
Logo: `Switchback trail line through two pines, forest green and trail tan`

### 78. Solstice Solar Co-op
`Solstice Solar Co-op` — raw idea · advisor

```text
Objective: Organize neighborhood group buys for rooftop solar at cooperative pricing.
Audience: Homeowners intimidated by solar sales calls and inconsistent quotes.
Edge: One vetted installer per cohort, one published price sheet, no commissioned salespeople.
Tone: Collective, transparent, openly critical of high-pressure solar sales.
```
Logo: `Sun disc segmented into shared panel squares, solar gold on slate`

### 79. Riverkeeper Labs
`Riverkeeper Labs` — named concept · copilot

```text
Objective: Sell water-quality test kits to community groups monitoring local waterways.
Audience: Volunteer watershed groups and science teachers without lab access.
Edge: Results upload to a shared public map that regulators actually reference.
Tone: Citizen-science empowering, methodologically strict, never alarmist without data.
```
Logo: `River bend forming a test vial outline, clear blue and lab white`

### 80. Packless
`Packless` — raw idea · copilot

```text
Objective: Run a refill store for household and personal care goods with no packaging.
Audience: Shoppers who want less plastic but will not drive across town for worse products.
Edge: Stocks only products that outperform their packaged equivalents on their own merits.
Tone: Pragmatic, low-guilt, dismissive of zero-waste perfectionism.
```
Logo: `Container silhouette drawn with a missing lid, kraft brown and clean white`

---

## Fashion & Lifestyle

### 81. Selvage Sunday
`Selvage Sunday` — named concept · copilot

```text
Objective: Build a raw denim repair and alteration studio with mail-in service.
Audience: Denim wearers who paid $200 for jeans and blew out the crotch in year two.
Edge: Chain-stitch hemming and darning matched to the original mill's fabric.
Tone: Craft-obsessed, patient, gently anti-replacement.
```
Logo: `Selvage line stitch forming a small sun, indigo and cotton white`

### 82. Ironwood Boots
`Ironwood Boots` — named concept · advisor

```text
Objective: Sell resoleable work boots direct, competing with heritage brands at half the price.
Audience: Tradespeople and outdoor workers who stand ten hours and resole rather than replace.
Edge: Stitchdown construction with a published resole network and cost.
Tone: Durable, unromantic about heritage myths, focused on the actual foot.
```
Logo: `Boot last profile with a visible welt stitch line, oxblood and iron`

### 83. Quietwear
`Quietwear` — raw idea · autonomous strategist

```text
Objective: Design adaptive clothing that does not look adaptive.
Audience: Adults with limited dexterity, wheelchair users, and caregivers buying for parents.
Edge: Magnetic and one-hand closures hidden inside conventional tailoring.
Tone: Dignified, style-first, never framing disability as inspiration.
```
Logo: `Two fabric edges meeting seamlessly, soft charcoal and bone`

### 84. Nine Knots
`Nine Knots` — named concept · copilot

```text
Objective: Sell sailing-inspired jewelry made from retired marine rope and salvaged brass.
Audience: Sailors and coastal visitors buying meaningful souvenirs, not tourist trinkets.
Edge: Each piece names the vessel and voyage its rope retired from.
Tone: Nautical, materially honest, restrained about maritime cliché.
```
Logo: `A single knot rendered as nine clean strands, brass on navy`

### 85. Pressline
`Pressline` — raw idea · copilot

```text
Objective: Run a letterpress studio doing wedding suites and small-run literary printing.
Audience: Couples and independent publishers who want a physical object worth keeping.
Edge: Prints on antique presses with hand-set type; every job shows its impression depth.
Tone: Tactile, craft-proud, honest about lead times.
```
Logo: `Impression indent forming a baseline rule, deep ink and paper cream`

### 86. Blunt Cut
`Blunt Cut` — named concept · copilot

```text
Objective: Open a gender-neutral barbershop with priced-by-service, not by gender.
Audience: Anyone tired of choosing between a barbershop and a salon that misreads them.
Edge: Price by clipper work and time, posted on the wall, same for everyone.
Tone: Direct, inclusive without a manifesto, confident about the haircut itself.
```
Logo: `Two clean shear lines meeting at a blunt edge, black and bright white`

### 87. Heirloom Mending
`Heirloom Mending` — raw idea · advisor

```text
Objective: Offer visible mending and textile restoration as a service and a class.
Audience: People with a moth-eaten sweater from a grandparent they cannot throw away.
Edge: Repairs are visible on purpose, documented with before and after photos.
Tone: Sentimental in the right way, skilled, unhurried.
```
Logo: `Sashiko stitch grid across a torn edge, indigo thread on natural linen`

### 88. Longshoreman Supply
`Longshoreman Supply` — named concept · copilot

```text
Objective: Sell workwear actually cut for women in industrial trades.
Audience: Welders, dock workers, and linewomen wearing badly fitted men's small.
Edge: Real sizing across body shapes, with the same ratings as the men's line.
Tone: Tough, unpatronizing, zero pink-it-and-shrink-it.
```
Logo: `Cargo hook forming a bold letterform, safety orange and canvas`

### 89. Slow Suitcase
`Slow Suitcase` — raw idea · copilot

```text
Objective: Sell travel goods for people committing to one carry-on for two weeks.
Audience: Frequent travelers who have decided checked bags are not worth it.
Edge: Every product is sold with a packing list it was designed to complete.
Tone: Minimal, systematic, quietly smug about walking past baggage claim.
```
Logo: `Suitcase outline reduced to one continuous line, muted olive and sand`

### 90. Terra Ceramica
`Terra Ceramica` — named concept · advisor

```text
Objective: Grow a pottery studio's handmade tableware line for restaurants and homes.
Audience: Chefs plating seasonal menus and home cooks replacing mass-market dishware.
Edge: Restaurant lines are made replaceable; broken pieces are matched years later.
Tone: Earthen, chef-fluent, practical about chipping and wear.
```
Logo: `Thrown-vessel profile curve with a wheel center dot, terracotta and glaze white`

---

## Personal Brands & Creators

### 91. Dr. Maya Osei
`Dr. Maya Osei` — existing project · advisor

```text
Objective: Build a science communication presence for a cardiologist explaining heart health.
Audience: Adults 40+ with a new diagnosis and a browser full of contradictory advice.
Edge: Every claim links the study and says plainly how strong the evidence is.
Tone: Warm, authoritative, allergic to supplement-influencer framing.
```
Logo: `Pulse line resolving into an open hand, deep red and clinical white`

### 92. Hollis Vane
`Hollis Vane` — named concept · copilot

```text
Objective: Position a solo product design consultancy against agencies for seed-stage clients.
Audience: Technical founders who need design leadership for eight weeks, not a full hire.
Edge: Fixed-scope engagements that end with a design system the team can run alone.
Tone: Senior, opinionated, comfortable saying no to bad scope.
```
Logo: `Weather vane arrow as a precise geometric mark, monochrome with one accent`

### 93. The Fermentation Desk
`The Fermentation Desk` — raw idea · copilot

```text
Objective: Grow a newsletter about home fermentation into a paid subscription.
Audience: Home cooks with one successful sourdough starter and a fear of botulism.
Edge: Every recipe includes the safety science, pH targets, and what failure looks like.
Tone: Curious, food-safe rigorous, funny about jars of regret.
```
Logo: `Airlock bubble rising in a jar neck, mustard and glass grey`

### 94. Ruth Okafor Speaks
`Ruth Okafor Speaks` — existing project · advisor

```text
Objective: Build a keynote speaking practice on workplace safety culture after 20 years in industry.
Audience: Operations and EHS leaders booking annual safety conferences.
Edge: Talks are built from real incident investigations she led, with permission.
Tone: Commanding, unflinching, genuinely moving without exploiting tragedy.
```
Logo: `Podium line and sound arc forming an initial O, industrial yellow and black`

### 95. Codewitch
`Codewitch` — named concept · autonomous strategist

```text
Objective: Grow a developer education brand teaching systems concepts to self-taught engineers.
Audience: Bootcamp graduates two years in who feel a gap around memory, networks, and databases.
Edge: Teaches by rebuilding small versions of real systems from scratch.
Tone: Irreverent, deeply technical, encouraging without dumbing anything down.
```
Logo: `Terminal cursor inside a crescent, phosphor green on deep purple`

### 96. The Retrofit Guy
`The Retrofit Guy` — existing project · copilot

```text
Objective: Turn a home efficiency YouTube channel into a consulting and course business.
Audience: Homeowners in older housing stock planning a five-year efficiency upgrade.
Edge: Every project is filmed with real cost, real permits, and real mistakes left in.
Tone: Handy, numbers-driven, dryly funny about contractor reality.
```
Logo: `House outline with one wall shown as insulation layers, work blue and orange`

### 97. Ana Builds
`Ana Builds` — named concept · copilot

```text
Objective: Grow a maker channel into a plans-and-hardware-kit business.
Audience: Weekend woodworkers with a modest garage shop and no space for a cabinet saw.
Edge: Every plan is buildable with five tools and lists the exact hardware, linked.
Tone: Encouraging, precise, honest about how long projects actually take.
```
Logo: `Speed square forming an A, workshop yellow and walnut`

### 98. Off-Hours Ops
`Off-Hours Ops` — raw idea · advisor

```text
Objective: Build a fractional COO practice for founder-led companies at 10-40 people.
Audience: Founders who are the bottleneck on every decision and know it.
Edge: 90-day engagements that install operating cadence, then deliberately step back.
Tone: Operator-blunt, systems-minded, uninterested in permanent dependency.
```
Logo: `Clock hand past the hour forming a check, deep teal and grey`

### 99. Rustbelt Recipes
`Rustbelt Recipes` — named concept · copilot

```text
Objective: Build a regional food-writing brand around Great Lakes industrial-town cooking.
Audience: Readers with family recipes from these towns and food writers tired of coastal focus.
Edge: Recipes are collected from named families with their stories and their exact measurements.
Tone: Affectionate, regionally proud, never ironic about casseroles.
```
Logo: `Fork tine profile stamped like a factory mark, oxidized orange on steel grey`

### 100. The Third Shift
`The Third Shift` — raw idea · advisor

```text
Objective: Build a career coaching practice for nurses leaving bedside work.
Audience: RNs with 5-15 years of experience who are burned out and think they have no options.
Edge: Coaches by clinical specialty into informatics, legal, education, and industry roles.
Tone: Peer-level, honest about the system, practical about the next paycheck.
```
Logo: `Three stacked shift bars with the third highlighted, scrub blue and warm white`

---

## Remix modifiers

Append any of these lines to a brief to change the output without rewriting it:

```text
Constraint: The name must work as a single-word domain and a spoken phone greeting.
Constraint: Must read as credible to a regulator or procurement officer.
Constraint: Palette must pass WCAG AA on both light and dark backgrounds.
Constraint: All copy must be readable at an 8th-grade level.
Constraint: The brand will be printed one-color on packaging as often as it appears on screen.
Posture: Take the boldest defensible position; avoid safe category language.
Posture: Stay conservative; this brand operates in a risk-averse industry.
Anti-goal: Do not sound like a venture-funded startup.
Anti-goal: Do not use "empower", "journey", "elevate", or "unlock".
```
