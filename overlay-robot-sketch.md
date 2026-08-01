# Sketch: robot drives OVER the card (two-canvas sandwich)

Supersedes `mobile-hero-sketch.md` — delete that file once this is applied.

Concept: one layout for all screen sizes. The card is fixed and centered (as in the
original design), and the world is split across two fullscreen canvases that
sandwich it:

```
z-index 20   fg canvas — particles + robot     (pointer-events: none)
z-index 10   info-card                          (links stay clickable)
z-index  0   bg canvas — landmarks
```

The robot and its particle cloud travel across the card; landmarks behind the card
show through the translucent blur as soft dots. The physics/filter code doesn't
change at all — only *where things are drawn*.

---

## 1. Route cell — two canvases

```python
Slam_World(Canvas(id="world"), Canvas(id="fg"))
```

## 2. CSS cell

Both canvases fullscreen-fixed; the fg one must ignore the mouse so the card's
links and internal scrolling keep working:

```css
slam-world canvas { position: fixed; inset: 0; display: block; width: 100%; height: 100%; }
#fg { z-index: 20; pointer-events: none; }
```

(The existing `slam-world { position: fixed; inset: 0; }` can stay; `#world` needs
no z-index — it sits at the bottom of the stack.)

Then shrink the mobile media query down to typography only — the layout is now the
same everywhere:

```css
@media (max-width: 600px) {
  info-card { width: 94vw; max-width: 94vw; max-height: 92vh; padding: 1.5rem 1.25rem; }
  info-card h1 { font-size: 1.6rem; }
  bio-text { font-size: 0.9rem; }
  hint-bar { display: none; }
}
```

Delete from the mobile block: `body { overflow: auto; }`, the `slam-world`
hero-band rules, and the `info-card` position/margin overrides. `body` keeps
`overflow: hidden` globally again (the card still scrolls internally via its own
`overflow-y: auto`).

## 3. JS cell

### 3a. Second context, size both canvases

```js
const cv  = document.getElementById('world'), ctx  = cv.getContext('2d');
const fcv = document.getElementById('fg'),    fctx = fcv.getContext('2d');

function sizeCanvas() {
  const dpr = devicePixelRatio || 1;
  W = innerWidth; H = innerHeight;                    // both are viewport-sized again
  for (const [c, x] of [[cv, ctx], [fcv, fctx]]) {
    c.width = W * dpr; c.height = H * dpr;
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
}
```

### 3b. initWorld — robot spawn-avoidance goes away

The robot is drawn on top now, so it's *supposed* to cross the card — no reason to
keep it away from the center:

```js
function initWorld() {
  robot.x = Math.random()*W; robot.y = Math.random()*H;
  robot.th = Math.random()*7;
  obstacles = [];
  const avoid = overlayMode() ? 180 : 0;   // keep landmarks visible around the card on desktop
  while (obstacles.length < 10) {
    const x = Math.random()*W, y = Math.random()*H;
    if (avoid && Math.hypot(x - W/2, y - H/2) < avoid) continue;
    obstacles.push({x, y});
  }
  scatter();
}
```

On phones the card covers most of the viewport, so landmark avoidance is
impossible — they just land where they land, and the ones under the card glow
through the blur. Sensing still works identically (the filter doesn't care what's
visible). If you find the desktop look better with landmarks under the card too,
delete the `avoid` logic entirely and `overlayMode` with it.

The debounced-resize handler from the last round stays exactly as is.

### 3c. draw — split across the two contexts

Landmarks on the bottom canvas, particles + robot on the top one:

```js
function drawRobot() {
  fctx.save(); fctx.translate(robot.x, robot.y); fctx.rotate(robot.th);
  fctx.fillStyle = '#6ba3ff';
  fctx.beginPath(); fctx.moveTo(14,0); fctx.lineTo(-10,-9); fctx.lineTo(-10,9); fctx.closePath(); fctx.fill();
  fctx.restore();
}

function draw() {
  ctx.clearRect(0,0,W,H); fctx.clearRect(0,0,W,H);
  ctx.fillStyle = '#2a2a40';
  for (const o of obstacles) { ctx.beginPath(); ctx.arc(o.x,o.y,5,0,7); ctx.fill(); }
  fctx.fillStyle = 'rgba(120,200,120,0.5)';
  for (const p of particles) { fctx.beginPath(); fctx.arc(p.x,p.y,1.5,0,7); fctx.fill(); }
  drawRobot();
  requestAnimationFrame(draw);
}
```

The landmark canvas only actually changes on `initWorld()`, so if you ever care
about battery you could draw it once instead of every frame — not worth the
complexity now.

### 3d. Keep from the previous round, unchanged

- Autopilot + "first arrow-key press takes over" (this is what makes the overlay
  design sing on mobile — the robot tours the card on its own).
- The `prefers-reduced-motion` guard.
- Debounced resize with the ±80px threshold.

---

## Readability tuning (do after you've seen it live)

Green dots at 0.5 alpha over body text is the one thing that might bother you.
Knobs, in the order I'd try them:

1. Drop particle alpha on the fg canvas to ~0.35.
2. Shrink fg particle radius 1.5 → 1.2.
3. Give the robot a dark outline (`fctx.strokeStyle='#0d0d17'; fctx.lineWidth=2; fctx.stroke()`
   after the fill) so it reads as "on top of" rather than "part of" the text.

Worst case the cloud converges *on* the card while the robot crosses it, text is
briefly speckled, and then the swarm moves on — that's the charm of it, not a bug.

## Cleanup

- Delete `mobile-hero-sketch.md`.
- Update the intro markdown cell (it still says "or tilt controls on mobile").
