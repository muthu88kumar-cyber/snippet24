const state = {

  articles: [],

  category: "All",

  speed: 60,

  search: "",

  location: {

    state: "",

    district: "",

    city: "",

    taluk: "",

    locality: ""

  }

};

const $ = selector =>

  document.querySelector(selector);

const $$ = selector =>

  [...document.querySelectorAll(selector)];

/* ==================================================

   LOAD ARTICLES

================================================== */

async function loadArticles() {

  setStatus("Loading latest stories...");

  try {

    const response =

      await fetch(

        `articles.json?t=${Date.now()}`

      );

    if (!response.ok) {

      throw new Error(

        `Unable to load articles: ${response.status}`

      );

    }

    const data =

      await response.json();

    state.articles =

      Array.isArray(data.articles)

        ? data.articles

        : [];

    render();

    updateTicker();

    setStatus(

      `${state.articles.length.toLocaleString()} stories`

    );

  } catch (error) {

    console.error(error);

    setStatus(

      "Unable to load stories."

    );

    const stories =

      $("#stories");

    if (stories) {

      stories.innerHTML = `

        <div class="empty-state">

          <h3>Stories unavailable</h3>

          <p>

            Please refresh and try again.

          </p>

        </div>

      `;

    }

  }

}

/* ==================================================

   BASIC HELPERS

================================================== */

function titleOf(article) {

  return (

    article.headline ||

    article.title ||

    "Untitled story"

  );

}

function summaryOf(article) {

  return (

    article.summary ||

    ""

  );

}

function pointsOf(article) {

  if (

    Array.isArray(article.snippet_lines)

  ) {

    return article.snippet_lines

      .filter(Boolean);

  }

  if (

    Array.isArray(article.key_points)

  ) {

    return article.key_points

      .filter(Boolean);

  }

  if (

    typeof article.snippet === "string"

  ) {

    return article.snippet

      .split("\n")

      .filter(Boolean);

  }

  return [];

}

function sourceOf(article) {

  return (

    article.original_source_url ||

    article.source_url ||

    ""

  );

}

function imageOf(article) {

  return article.image_url || "";

}

function categoryOf(article) {

  const raw =

    article.category || "";

  const mapping = {

    "In India": "India",

    "Business & Economy": "Money",

    "Tech & AI": "Tech",

    "Society & Culture": "People",

    "Human & Environment": "Environment"

  };

  if (mapping[raw]) {

    if (

      raw === "In India" &&

      looksLikeSports(article)

    ) {

      return "Sports";

    }

    return mapping[raw];

  }

  return raw;

}

/* ==================================================

   SPORTS DETECTION

================================================== */

function looksLikeSports(article) {

  const text = [

    titleOf(article),

    summaryOf(article),

    ...pointsOf(article)

  ]

    .join(" ")

    .toLowerCase();

  const terms = [

    "cricket",

    "football",

    "badminton",

    "tennis",

    "hockey",

    "pickleball",

    "olympic",

    "athlete",

    "championship",

    "tournament",

    "world cup",

    "match",

    "shuttler",

    "medal",

    "wicket",

    "goal",

    "league",

    "sport",

    "ipl",

    "fifa",

    "bcci",

    "icc"

  ];

  return terms.some(

    term => text.includes(term)

  );

}

/* ==================================================

   READING MODES

================================================== */

function getReading(article) {

  const reading =

    article.reading;

  if (reading) {

    if (state.speed === 10) {

      return {

        label: "KNOW",

        blocks: [

          reading["10_sec"] ||

          titleOf(article)

        ].filter(Boolean)

      };

    }

    if (state.speed === 60) {

      const data =

        reading["60_sec"] || {};

      return {

        label: "UNDERSTAND",

        blocks: [

          data.what_happened,

          data.why_it_matters

        ].filter(Boolean)

      };

    }

    if (state.speed === 180) {

      const data =

        reading["3_min"] || {};

      return {

        label: "THINK",

        blocks: [

          data.what_happened,

          data.why_it_matters,

          data.who_is_affected,

          data.whats_next

        ].filter(Boolean)

      };

    }

  }

  /*

   * Compatibility for older articles.

   */

  const points =

    pointsOf(article);

  if (state.speed === 10) {

    return {

      label: "KNOW",

      blocks: [

        points[0] ||

        titleOf(article)

      ]

    };

  }

  if (state.speed === 60) {

    return {

      label: "UNDERSTAND",

      blocks: [

        ...points,

        summaryOf(article)

      ].filter(Boolean)

    };

  }

  return {

    label: "THINK",

    blocks: [

      ...points,

      summaryOf(article)

    ].filter(Boolean)

  };

}

/* ==================================================

   LOCATION

================================================== */

function loadLocation() {

  try {

    const saved =

      localStorage.getItem(

        "snippet24_location"

      );

    if (saved) {

      state.location =

        JSON.parse(saved);

    }

  } catch (error) {

    console.warn(

      "Location could not be loaded."

    );

  }

  updateLocationText();

}

function saveLocation() {

  state.location = {

    state:

      $("#stateSelect")?.value || "",

    district:

      $("#districtInput")?.value.trim() || "",

    city:

      $("#cityInput")?.value.trim() || "",

    taluk:

      $("#talukInput")?.value.trim() || "",

    locality:

      $("#localityInput")?.value.trim() || ""

  };

  localStorage.setItem(

    "snippet24_location",

    JSON.stringify(state.location)

  );

  updateLocationText();

  $("#locationPanel")?.classList.remove(

    "open"

  );

  state.category = "Local";

  render();

}

function updateLocationText() {

  const locationText =

    $("#locationText");

  if (!locationText) {

    return;

  }

  const location =

    state.location;

  const parts = [

    location.city,

    location.district,

    location.state

  ].filter(Boolean);

  locationText.textContent =

    parts.length

      ? parts.join(", ")

      : "Set your location";

}

function articleMatchesLocation(article) {

  const location =

    state.location;

  const text = [

    titleOf(article),

    summaryOf(article),

    ...pointsOf(article),

    article.location?.state || "",

    article.location?.district || "",

    article.location?.city || "",

    article.location?.taluk || "",

    article.location?.locality || "",

    article.state || "",

    article.district || "",

    article.city || "",

    article.taluk || "",

    article.locality || ""

  ]

    .join(" ")

    .toLowerCase();

  const terms = [

    location.locality,

    location.taluk,

    location.city,

    location.district,

    location.state

  ]

    .filter(Boolean)

    .map(value =>

      value.toLowerCase()

    );

  if (!terms.length) {

    return false;

  }

  return terms.some(

    term => text.includes(term)

  );

}

/* ==================================================

   FILTER

================================================== */

function filteredArticles() {

  let stories =

    [...state.articles];

  if (state.category === "Local") {

    const local =

      stories.filter(

        article =>

          articleMatchesLocation(article)

      );

    stories =

      local.length

        ? local

        : stories.filter(

            article =>

              categoryOf(article) === "India"

          );

  } else if (

    state.category !== "All"

  ) {

    stories =

      stories.filter(

        article =>

          categoryOf(article) ===

          state.category

      );

  }

  if (state.search.trim()) {

    const query =

      state.search

        .trim()

        .toLowerCase();

    stories =

      stories.filter(article => {

        const searchable = [

          titleOf(article),

          summaryOf(article),

          ...pointsOf(article),

          article.publisher || "",

          article.category || "",

          article.location?.city || "",

          article.location?.district || "",

          article.location?.state || ""

        ]

          .join(" ")

          .toLowerCase();

        return searchable.includes(query);

      });

  }

  return stories;

}

/* ==================================================

   STORY CARD

================================================== */

function createStoryCard(article) {

  const card =

    document.createElement("article");

  card.className =

    "story-card";

  card.dataset.id =

    article.id || "";

  const reading =

    getReading(article);

  const title =

    titleOf(article);

  const category =

    categoryOf(article);

  const publisher =

    article.publisher || "";

  const source =

    sourceOf(article);

  const image =

    imageOf(article);

  let html = "";

  if (image) {

    html += `

      <div class="story-image">

        <img

          src="${escapeAttr(image)}"

          alt=""

          loading="lazy"

          onerror="

            this.parentElement.style.display='none'

          "

        >

      </div>

    `;

  }

  html += `

    <div class="story-content">

      <div class="story-meta">

        <span class="story-category">

          ${escapeHtml(category)}

        </span>

        ${

          publisher

            ? `

              <span class="story-publisher">

                ${escapeHtml(publisher)}

              </span>

            `

            : ""

        }

      </div>

      <h2 class="story-title">

        ${escapeHtml(title)}

      </h2>

      <div class="reading-label">

        ${escapeHtml(reading.label)}

      </div>

      <div class="story-reading">

        ${

          reading.blocks

            .map(

              block =>

                `<p>${escapeHtml(block)}</p>`

            )

            .join("")

        }

      </div>

      <div class="story-footer">

        ${

          source

            ? `

              <a

                class="source-link"

                href="${escapeAttr(source)}"

                target="_blank"

                rel="noopener noreferrer"

              >

                Original source →

              </a>

            `

            : ""

        }

        <span class="editorial-note">

          ${

            article.editorial_note ||

            "Rephrased from the original source for clarity."

          }

        </span>

      </div>

    </div>

  `;

  card.innerHTML = html;

  return card;

}

/* ==================================================

   RENDER

================================================== */

function render() {

  const container =

    $("#stories");

  if (!container) {

    return;

  }

  const stories =

    filteredArticles();

  container.innerHTML = "";

  if (!stories.length) {

    container.innerHTML = `

      <div class="empty-state">

        <h3>No stories found</h3>

        <p>

          Try another category or search.

        </p>

      </div>

    `;

    syncControls();

    return;

  }

  const fragment =

    document.createDocumentFragment();

  stories.forEach(article => {

    fragment.appendChild(

      createStoryCard(article)

    );

  });

  container.appendChild(

    fragment

  );

  syncControls();

}

/* ==================================================

   SPEED

================================================== */

function setSpeed(speed) {

  state.speed =

    Number(speed);

  render();

  $("#signal")?.scrollIntoView({

    behavior: "smooth",

    block: "start"

  });

}

/* ==================================================

   CATEGORY

================================================== */

function setCategory(category) {

  state.category =

    category;

  state.search = "";

  const input =

    $("#searchInput");

  if (input) {

    input.value = "";

  }

  render();

  $("#signal")?.scrollIntoView({

    behavior: "smooth",

    block: "start"

  });

}

/* ==================================================

   CATCH ME UP

================================================== */

function catchMeUp() {

  state.category = "All";

  state.speed = 60;

  state.search = "";

  const input =

    $("#searchInput");

  if (input) {

    input.value = "";

  }

  render();

  $("#signal")?.scrollIntoView({

    behavior: "smooth",

    block: "start"

  });

}

/* ==================================================

   CONTROLS

================================================== */

function syncControls() {

  $$("[data-speed]")

    .forEach(button => {

      const active =

        Number(button.dataset.speed) ===

        state.speed;

      button.classList.toggle(

        "active",

        active

      );

    });

  $$(".nav-item[data-category]")

    .forEach(button => {

      button.classList.toggle(

        "active",

        button.dataset.category ===

        state.category

      );

    });

}

/* ==================================================

   SEARCH

================================================== */

function openSearch() {

  const panel =

    $("#searchPanel");

  if (!panel) {

    return;

  }

  panel.classList.add("open");

  panel.setAttribute(

    "aria-hidden",

    "false"

  );

  $("#searchInput")?.focus();

  renderSearchResults();

}

function closeSearch() {

  const panel =

    $("#searchPanel");

  if (!panel) {

    return;

  }

  panel.classList.remove("open");

  panel.setAttribute(

    "aria-hidden",

    "true"

  );

}

function searchArticles() {

  state.search =

    $("#searchInput")?.value || "";

  renderSearchResults();

  render();

}

function renderSearchResults() {

  const results =

    $("#searchResults");

  if (!results) {

    return;

  }

  const query =

    state.search

      .trim()

      .toLowerCase();

  if (!query) {

    results.innerHTML = "";

    return;

  }

  const matches =

    state.articles

      .filter(article => {

        const text = [

          titleOf(article),

          summaryOf(article),

          ...pointsOf(article),

          article.publisher || "",

          article.category || "",

          article.location?.city || "",

          article.location?.district || ""

        ]

          .join(" ")

          .toLowerCase();

        return text.includes(query);

      })

      .slice(0, 30);

  if (!matches.length) {

    results.innerHTML = `

      <div class="empty-state">

        No matching stories.

      </div>

    `;

    return;

  }

  results.innerHTML =

    matches.map(article => `

      <button

        class="search-result"

        data-story-id="${escapeAttr(article.id)}"

        type="button"

      >

        <strong>

          ${escapeHtml(

            titleOf(article)

          )}

        </strong>

        <small>

          ${escapeHtml(

            categoryOf(article)

          )}

        </small>

      </button>

    `).join("");

}

/* ==================================================

   LIVE TICKER

================================================== */

function updateTicker() {

  const ticker =

    $("#liveTicker");

  if (!ticker) {

    return;

  }

  const latest =

    state.articles

      .slice(0, 8)

      .map(article =>

        titleOf(article)

      )

      .filter(Boolean);

  ticker.textContent =

    latest.length

      ? latest.join("  •  ")

      : "Latest updates will appear here.";

}

/* ==================================================

   STATUS

================================================== */

function setStatus(text) {

  const status =

    $("#status");

  if (status) {

    status.textContent = text;

  }

}

/* ==================================================

   SECURITY / HTML ESCAPING

================================================== */

function escapeHtml(value) {

  return String(value ?? "")

    .replaceAll("&", "&amp;")

    .replaceAll("<", "&lt;")

    .replaceAll(">", "&gt;")

    .replaceAll('"', "&quot;")

    .replaceAll("'", "&#039;");

}

function escapeAttr(value) {

  return escapeHtml(value);

}

/* ==================================================

   EVENTS

================================================== */

document.addEventListener(

  "click",

  event => {

    const speedButton =

      event.target.closest(

        "[data-speed]"

      );

    if (speedButton) {

      setSpeed(

        speedButton.dataset.speed

      );

      return;

    }

    const categoryButton =

      event.target.closest(

        "[data-category]"

      );

    if (categoryButton) {

      setCategory(

        categoryButton.dataset.category

      );

      $("#moreMenu")

        ?.classList.remove("open");

      return;

    }

    const result =

      event.target.closest(

        "[data-story-id]"

      );

    if (result) {

      const id =

        result.dataset.storyId;

      const card =

        document.querySelector(

          `.story-card[data-id="${CSS.escape(id)}"]`

        );

      closeSearch();

      card?.scrollIntoView({

        behavior: "smooth",

        block: "center"

      });

    }

  }

);

/* ==================================================

   SEARCH EVENTS

================================================== */

$("#searchBtn")

  ?.addEventListener(

    "click",

    openSearch

  );

$("#closeSearch")

  ?.addEventListener(

    "click",

    closeSearch

  );

$("#searchInput")

  ?.addEventListener(

    "input",

    searchArticles

  );

/* ==================================================

   MENU

================================================== */

$("#menuBtn")

  ?.addEventListener(

    "click",

    () => {

      $("#mainNav")

        ?.classList.toggle("open");

    }

  );

$("#moreBtn")

  ?.addEventListener(

    "click",

    event => {

      event.stopPropagation();

      $("#moreMenu")

        ?.classList.toggle("open");

    }

  );

document.addEventListener(

  "keydown",

  event => {

    if (event.key === "Escape") {

      closeSearch();

      $("#moreMenu")

        ?.classList.remove("open");

      $("#locationPanel")

        ?.classList.remove("open");

    }

  }

);

/* ==================================================

   LOCATION EVENTS

================================================== */

$("#locationBtn")

  ?.addEventListener(

    "click",

    () => {

      $("#locationPanel")

        ?.classList.toggle("open");

    }

  );

$("#saveLocation")

  ?.addEventListener(

    "click",

    saveLocation

  );

/* ==================================================

   REFRESH

================================================== */

$("#refreshBtn")

  ?.addEventListener(

    "click",

    loadArticles

  );

/* ==================================================

   CATCH ME UP

================================================== */

$("#catchupBtn")

  ?.addEventListener(

    "click",

    catchMeUp

  );

/* ==================================================

   YEAR

================================================== */

const year =

  $("#year");

if (year) {

  year.textContent =

    new Date().getFullYear();

}

/* ==================================================

   START

================================================== */

loadLocation();

loadArticles();