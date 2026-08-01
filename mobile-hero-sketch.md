# Sketch: mobile hero-band layout + autopilot robot

Goal: on phones, stop using the sim as a fullscreen background. The page becomes a
normal scrolling page — a 40vh canvas "hero" at the top, the info card in normal
flow below it. The robot drives itself (autopilot), so there are no controls to
explain and the tilt-permission flow can be deleted entirely. Desktop stays exactly
as it is today, except the robot also autopilots until the first arrow-key press.

Everything below maps onto the existing cells in `app.ipynb`.

---

## 1. CSS cell — replace the `@media (max-width: 600px)` block

Desktop rules stay untouched. The mobile block flips the page from
"fixed overlay" to "document flow":

```css
@media (max-width: 600px) {
  body { overflow: auto; }                      /* page scrolls normally again */

  slam-world { position: relative; inset: auto; display: block; height: 40svh; }
  /* svh = small viewport height: sized as if the address bar is visible,
     so the browser chrome appearing/disappearing never resizes the canvas.
     Fallback for old browsers: add `height: 40vh;` on the line before. */

  info-card {
    position: static; transform: none;
    width: auto; max-width: none; max-height: none; overflow: visible;
    margin: -1.5rem 3vw 2rem;                   /* slight overlap onto the hero */
    padding: 1.5rem 1.25rem;
    border-radius: 1rem;
  }
  info-card h1 { font-size: 1.6rem; }
  bio-text { font-size: 0.9rem; }
  hint-bar { display: none; }
}
```

Delete the old `tilt-btn` rules (both the base `tilt-btn { display:none; }` and the
mobile block's version) — tilt is going away.

The negative top margin makes the card overlap the bottom edge of the hero, which
reads as intentional design rather than two stacked boxes. Tune to taste.

---

## 2. JS cell — three changes

### 2a. Size from the canvas element, not the window

The canvas is no longer always fullscreen, so `innerWidth/innerHeight` is wrong on
mobile. Measure the element itself — this works in both layouts:

```js
function sizeCanvas() {
  const dpr = devicePixelRatio || 1;
  const r = cv.getBoundingClientRect();
  W = r.width; H = r.height;
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
```

(Drop the `cv.style.width/height` lines — CSS owns the element size now.)

### 2b. Split world init from canvas sizing (fixes the reset-on-resize bug)

`initWorld()` runs once at load; `sizeCanvas()` runs on resize. The card only
overlaps the canvas on desktop, so the "keep things away from the center" logic
becomes conditional:

```js
const overlayMode = () => matchMedia('(min-width: 601px)').matches;

function initWorld() {
  const avoid = overlayMode() ? 200 : 0;   // card overlaps canvas only on desktop
  do { robot.x = Math.random()*W; robot.y = Math.random()*H; }
  while (Math.hypot(robot.x - W/2, robot.y - H/2) < avoid);
  robot.th = Math.random()*7;
  obstacles = [];
  while (obstacles.length < 10) {          // retry instead of skip: always 10 landmarks
    const x = Math.random()*W, y = Math.random()*H;
    if (Math.hypot(x - W/2, y - H/2) < avoid * 0.9) continue;
    obstacles.push({x, y});
  }
  scatter();
}

let rsTimer;
addEventListener('resize', () => {
  clearTimeout(rsTimer);
  rsTimer = setTimeout(() => {
    const oldW = W, oldH = H;
    sizeCanvas();
    // Only rebuild the world on a real layout change (rotation, window resize),
    // not tiny chrome-induced wiggles:
    if (Math.abs(W - oldW) > 80 || Math.abs(H - oldH) > 80) initWorld();
  }, 150);
});

sizeCanvas(); initWorld();
```

### 2c. Autopilot replaces tilt

Delete: `tiltOn`, `tiltX`, `tiltY`, `onTilt`, `enableTilt`, `window.enableTilt`,
and the `if (tiltOn) {...}` branch in the interval loop.

Add a wander behaviour. It picks a random heading every couple of seconds, steers
toward it, and steers back toward the middle when it gets near an edge. First
arrow-key press hands control to the user (desktop only, effectively — phones have
no arrows, so mobile just stays on autopilot forever):

```js
let auto = true, targetTh = 0, wanderTicks = 0;

function autopilot() {
  const margin = Math.min(W, H) * 0.15;
  if (robot.x < margin || robot.x > W - margin || robot.y < margin || robot.y > H - margin) {
    targetTh = Math.atan2(H/2 - robot.y, W/2 - robot.x);   // head back toward center
  } else if (--wanderTicks <= 0) {
    targetTh = Math.random() * 2 * Math.PI;
    wanderTicks = 25 + Math.random() * 50;                 // new heading every ~1.5-4.5s
  }
  let diff = targetTh - robot.th;
  diff = Math.atan2(Math.sin(diff), Math.cos(diff));       // wrap to [-pi, pi]
  const dth = Math.max(-0.06, Math.min(0.06, diff));
  return { dx: Math.cos(robot.th) * 2.5, dy: Math.sin(robot.th) * 2.5, dth };
}
```

And the interval loop becomes:

```js
setInterval(() => {
  let dx = 0, dy = 0, dth = 0;
  if (keys.ArrowLeft)  dth -= 0.08;
  if (keys.ArrowRight) dth += 0.08;
  if (keys.ArrowUp)   { dx =  Math.cos(robot.th)*4; dy =  Math.sin(robot.th)*4; }
  if (keys.ArrowDown) { dx = -Math.cos(robot.th)*4; dy = -Math.sin(robot.th)*4; }
  if (dx || dy || dth) auto = false;                       // user takes over
  if (auto) ({dx, dy, dth} = autopilot());
  if (dx || dy || dth) move(dx, dy, dth);
  else for (const p of particles) { p.x += gauss()*3; p.y += gauss()*3; }
}, 60);
```

Notes:
- Autopilot speed 2.5 (vs. 4 for manual) keeps the idle animation calm.
- The idle-diffusion branch now only runs after the user takes over and then stops
  — autopilot means the robot is almost always moving, so the particle cloud stays
  converged and the demo always looks alive.
- Bonus a11y: wrap the interval body in
  `if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;`
  to freeze the sim for users who ask for reduced motion.

---

## 3. Route cell — remove the tilt button

- Delete `Tilt_Btn(...)` from the `index()` return value.
- Delete `Tilt_Btn` from the imports cell, and update the hint bar copy if you like
  ("Arrow keys to take the wheel" now that it autopilots).

---

## Order of application

1. CSS block (section 1) — page is immediately usable on mobile even before JS changes.
2. JS sizing/init split (2a + 2b) — fixes the resize bug on both layouts.
3. Autopilot + tilt removal (2c + 3) — the payoff.

Each step is independently shippable, so you can do them as three separate
dialog turns in solveit and eyeball the page between each.
