const portalButton = document.getElementById("portalButton");
const portalMenu = document.getElementById("portalMenu");
const mobileToggle = document.getElementById("mobileToggle");
const navLinks = document.getElementById("navLinks");
const toast = document.getElementById("toast");

function closePortalMenu() {
  if (!portalMenu) return;
  portalMenu.hidden = true;
  portalButton?.setAttribute("aria-expanded", "false");
}

portalButton?.addEventListener("click", (event) => {
  event.stopPropagation();
  const open = portalMenu.hidden;
  portalMenu.hidden = !open;
  portalButton.setAttribute("aria-expanded", String(open));
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".portal-access")) closePortalMenu();
});

mobileToggle?.addEventListener("click", () => {
  const open = navLinks.classList.toggle("mobile-open");
  mobileToggle.setAttribute("aria-expanded", String(open));
});

navLinks?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.classList.remove("mobile-open");
    mobileToggle?.setAttribute("aria-expanded", "false");
  });
});


// Hero value-chain animation.
// A single horizontal track contains FARMER → PADDY → MILL → RICE → WORLD.
// We translate that track so the ACTIVE WORD is always exactly at the visual
// center. Because the arrows live on the same track, they travel with the
// words instead of appearing/disappearing independently.
const chainItems = [
  { name: "FARMER", caption: "Field" },
  { name: "PADDY", caption: "Crop" },
  { name: "MILL", caption: "Processing" },
  { name: "RICE", caption: "Product" },
  { name: "WORLD", caption: "Market" }
];

const chainVisual = document.querySelector(".hero-chain-visual");
const chainViewport = document.querySelector(".chain-track-viewport");
const chainTrack = document.querySelector(".chain-track");
const chainWords = [...document.querySelectorAll(".track-word")];
const chainArrows = [...document.querySelectorAll(".track-arrow")];
const flowCaption = document.querySelector(".active-caption");

let chainIndex = 0;
let chainTimer = null;

function centerActiveWord(index, animate = true) {
  if (!chainViewport || !chainTrack || !chainWords[index]) return;

  const viewportCenter = chainViewport.clientWidth / 2;
  const word = chainWords[index];

  // Word center in the track's coordinate system.
  const wordCenter = word.offsetLeft + word.offsetWidth / 2;

  chainTrack.style.transition = animate
    ? "transform 1.05s cubic-bezier(.22,1,.36,1)"
    : "none";

  chainTrack.style.transform =
    `translate(calc(${viewportCenter - wordCenter}px), -50%)`;
}

function setChainProgress(index) {
  progress.forEach((dot, i) => dot.classList.toggle("active", i === index));
}

function updateCaption(index) {
  if (!flowCaption) return;
  flowCaption.classList.add("caption-changing");

  window.setTimeout(() => {
    flowCaption.textContent = chainItems[index].caption;
    flowCaption.classList.remove("caption-changing");
  }, 260);
}

function transitionChain() {
  const nextIndex = (chainIndex + 1) % chainItems.length;

  // The whole physical chain moves. The arrow between the current and next
  // word is therefore part of the exact same motion.
  centerActiveWord(nextIndex, true);

  updateCaption(nextIndex);
  chainIndex = nextIndex;
}

function startChainTimer() {
  window.clearInterval(chainTimer);
  chainTimer = window.setInterval(transitionChain, 3500);
}

function initChain() {
  if (!chainVisual || !chainViewport || !chainTrack || !chainWords.length) return;

  // First stage is centered before the visitor sees movement.
  centerActiveWord(0, false);
  if (flowCaption) flowCaption.textContent = chainItems[0].caption;

  startChainTimer();

  window.addEventListener("resize", () => centerActiveWord(chainIndex, false));

  chainVisual.addEventListener("mouseenter", () => {
    window.clearInterval(chainTimer);
  });

  chainVisual.addEventListener("mouseleave", startChainTimer);
}

initChain();

document.querySelectorAll("[data-coming-soon], .coming-soon-link").forEach((element) => {
  element.addEventListener("click", () => {
    toast?.classList.add("show");
    window.clearTimeout(window.__annyadataToastTimer);
    window.__annyadataToastTimer = window.setTimeout(() => {
      toast?.classList.remove("show");
    }, 2200);
  });
});
