# Sketch: kidnap the robot

Click/tap anywhere in the world → the robot teleports there → the particle filter
has to figure out where it went. This is the *kidnapped robot problem*, the
canonical stress test for Monte-Carlo localization — so the feature doubles as the
most honest demo on the page.

The story a visitor sees:

1. Click. Poof-ring at the old spot, poof-ring at the new spot, robot appears there.
2. The particle cloud is now confidently *wrong* — it stays where the robot used to be.
3. The filter notices it's lost (all weights collapse) and sprays random guesses
   across the map — global relocalization.
4. Guesses near the robot survive resampling, and within a few seconds the cloud
   snaps onto the robot's new home. Confidence readout crashes, then climbs back.

Steps 3–4 are not scripted animation — they're the real algorithm recovering.
That's the whole charm.

---

## 1. Why the filter needs one real fix first (particle deprivation)

Current weighting: `p.w = Math.exp(-e/(2*60*60))`. After a kidnap every particle's
error `e` is huge, all weights underflow to exactly 0, `sum` is 0, and the
low-variance resampler degenerates (with all-zero cumulative weights it copies one
arbitrary particle N times). The cloud collapses to a dot nowhere near the robot
and recovery is glacial or never. Real MCL solves this by **injecting random
particles when the filter is lost**. In `update()`, right after computing `sum`:

```js
  // Lost? All weights underflowed — the cloud is confidently wrong.
  // Global relocalization: replace a chunk with uniform random guesses
  // and skip this round of resampling (it would be resampling noise).
  if (sum < 1e-8) {
    for (let k = 0; k < N * 0.25; k++) {
      const j = Math.floor(Math.random() * N);
      particles[j] = {x: Math.random()*W, y: Math.random()*H, th: robot.th, w: 1/N};
    }
    for (const p of particles) p.w = 1/N;
    return;
  }
```

Each tick while lost, another 25% of particles get re-rolled — so within a few
updates some land near the robot, out-weigh everything, and resampling does the
rest. Tuning notes:

- `1e-8` threshold: with your constants, a cloud ~300px off already underflows to
  0, so anything tiny works. If recovery ever triggers during normal driving,
  lower it.
- `0.25` injection fraction: higher = faster recovery, lower = more dramatic
  "searching" phase. 0.15–0.3 all look good; start at 0.25.
- Keep the robot's heading for injected particles (`th: robot.th`) — heading isn't
  part of the sensor model anyway, and it avoids visual weirdness if you ever draw
  particle headings.

This fix is worth having even without the kidnap feature — it also rescues the
filter if idle diffusion ever drifts the cloud too far.

## 2. The kidnap itself (route/JS)

Clicks land on the page everywhere except the card (the fg canvas is
`pointer-events: none`, so it never eats them). One listener, filtered so links,
the card, and the hint bar are exempt:

```js
addEventListener('click', e => {
  if (e.target.closest('info-card, hint-bar, a, button')) return;
  kidnap(e.clientX, e.clientY);
});

function kidnap(x, y) {
  poof(robot.x, robot.y);          // departure marker
  robot.x = x; robot.y = y;
  robot.th = Math.random()*7;
  poof(x, y);                      // arrival marker
  auto = true; wanderTicks = 0;    // autopilot resumes from the new spot immediately
}
```

`clientX/Y` are already in the same CSS-pixel space as the canvas coordinates
(fixed inset-0 canvas, dpr handled via `setTransform`), so no conversion needed.

Re-enabling `auto` matters: `update()` only runs inside `move()`, so the robot has
to be moving for the filter to recover. Autopilot guarantees the show goes on even
if the visitor just clicks once and watches.

## 3. Poof rings (fg canvas)

Tiny ripple system, drawn on the fg context so rings sweep over the card too:

```js
let ripples = [];
function poof(x, y) { ripples.push({x, y, r: 6, a: 0.9}); }

// inside draw(), after drawRobot():
ripples = ripples.filter(rp => rp.a > 0.02);
for (const rp of ripples) {
  fctx.beginPath(); fctx.arc(rp.x, rp.y, rp.r, 0, 7);
  fctx.strokeStyle = `rgba(107,163,255,${rp.a})`;
  fctx.lineWidth = 2; fctx.stroke();
  rp.r += 3; rp.a *= 0.9;
}
```

~0.5s expanding ring, self-cleaning, no timers.

## 4. Confidence readout (makes the recovery legible)

Without a number, non-robotics visitors see "dots scattered, dots gathered".
With one, they see *the robot got lost and found itself*. Mean distance from the
particle centroid, mapped to a percentage:

```js
function confidence() {
  let mx = 0, my = 0;
  for (const p of particles) { mx += p.x; my += p.y; }
  mx /= N; my /= N;
  let s = 0;
  for (const p of particles) s += Math.hypot(p.x - mx, p.y - my);
  return Math.max(0, Math.min(1, 1 - (s/N) / (0.35 * Math.hypot(W, H))));
}
```

Update the hint bar every few ticks (e.g. in the 60ms loop, every 5th tick):

```js
const hint = document.querySelector('hint-bar');
let tick = 0;
// in the interval:
if (++tick % 5 === 0 && hint)
  hint.textContent = `click anywhere to kidnap the robot · localization confidence ${Math.round(confidence()*100)}%`;
```

Watching it read 97% → 8% → 95% over four seconds after a kidnap *is* the demo.

CSS: hint-bar is `display:none` on mobile. Consider showing it there now (it earns
its pixels once it explains the tap), maybe as a smaller strip pinned to the very
bottom.

## 5. Mobile notes

- Tap = same `click` listener, nothing extra needed.
- The card covers most of a phone screen, so the tappable world is the border
  around it. Two mitigations, pick either or both:
  - Cap the card at ~80svh on mobile (instead of 92vh) so there's a real tap zone
    at the bottom — which is also where the hint text sits.
  - Treat a tap on non-interactive parts of the card as a kidnap *at that point*
    too (drop `info-card` from the closest() filter, keep `a, button`). The robot
    getting dumped right onto the bio is very on-brand for this design.

## 6. Optional theater (only if you're having fun)

- **Abduction tween**: instead of instant teleport, scale the robot up + fade out
  over ~200ms at the old spot, then fade in at the new one. ~15 lines with a
  `kidnapT` counter in `draw()`.
- **Drag to abduct**: pointerdown near the robot picks it up, it follows the
  pointer, release drops it. Crucially, don't call `move()` while dragging —
  the odometry "doesn't see" the abduction, which is exactly what makes it a
  kidnap. More code (pointer capture, distinguishing drag from tap), so do it
  only if the click version leaves you wanting.
- **Kidnap counter easter egg**: after the 3rd kidnap, hint bar briefly reads
  "the robot has been kidnapped 3 times today. it is doing fine." — then back to
  normal.

## 7. Copy/docs cleanup

- Intro markdown cell: add the kidnapped-robot bit to the description.
- The `update` bullet in the particle-filter markdown cell: mention the
  lost-detection + random-injection branch (it's the most educational part of the
  file now).
- Hint bar copy replaces "Use arrow keys to drive the robot" — arrows still work
  and take over from autopilot, but kidnapping is the headline interaction.

## Suggested order

1. Section 1 (injection fix) — ship alone, verify normal driving is unaffected.
2. Sections 2+3 (kidnap + poofs) — the feature.
3. Section 4 (confidence) — the narration.
4. Sections 5/6 to taste.
