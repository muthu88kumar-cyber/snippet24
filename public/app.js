/* =========================================================
   SNIPPET24
   FRONTEND APPLICATION
========================================================= */

"use strict";


/* =========================================================
   CONFIGURATION
========================================================= */

const API_BASE = "/api";

const LANGUAGES = {
  en: "English",
  ta: "தமிழ்",
  te: "తెలుగు",
  kn: "ಕನ್ನಡ",
  ml: "മലയാളം",
  hi: "हिन्दी"
};

const CATEGORY_NAMES = [
  "In India",
  "Global",
  "Security & Peace",
  "Law Around Us",
  "Science & Development",
  "Business & Economy",
  "Society & Culture",
  "Human & Environment",
  "Tech & AI",
  "Sports"
];


/* =========================================================
   APPLICATION STATE
========================================================= */

const state = {
  language: "en",
  category: "all",
  search: "",
  stories: [],
  allStories: [],
  loading: false
};


/* =========================================================
   DOM HELPERS
========================================================= */

function $(selector) {
  return document.querySelector(selector);
}

function $$(selector) {
  return Array.from(
    document.querySelectorAll(selector)
  );
}


/* =========================================================
   TEXT HELPERS
========================================================= */

function escapeHTML(value) {

  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function cleanText(value) {

  return String(value || "")
    .replace(/\s+/g, " ")
    .trim();
}


/* =========================================================
   DATE / TIME
========================================================= */

function formatDate(value) {

  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString(
    undefined,
    {
      day: "2-digit",
      month: "short",
      year: "numeric"
    }
  );
}


function formatTime(value) {

  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleTimeString(
    undefined,
    {
      hour: "2-digit",
      minute: "2-digit"
    }
  );
}


/* =========================================================
   LIVE CLOCK
========================================================= */

function startClock() {

  const clock =
    $("#clock");

  if (!clock) {
    return;
  }

  function updateClock() {

    const now = new Date();

    clock.textContent =
      now.toLocaleTimeString(
        undefined,
        {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit"
        }
      );
  }

  updateClock();

  setInterval(
    updateClock,
    1000
  );
}


/* =========================================================
   LANGUAGE
========================================================= */

function getStoryLanguage(story) {

  if (
    story &&
    story.translations &&
    story.translations[state.language]
  ) {

    return story.translations[state.language];
  }

  if (
    story &&
    story.translations &&
    story.translations.en
  ) {

    return story.translations.en;
  }

  return {
    headline:
      story?.snippet24?.headline ||
      story?.source?.title ||
      "Untitled story",

    summary:
      story?.snippet24?.summary ||
      "",

    keyPoints:
      story?.snippet24?.keyPoints ||
      []
  };
}


/* =========================================================
   LANGUAGE BUTTONS
========================================================= */

function setupLanguageButtons() {

  const buttons =
    $$(".language");

  buttons.forEach(
    button => {

      button.addEventListener(
        "click",
        () => {

          const lang =
            button.dataset.lang;

          if (
            !LANGUAGES[lang]
          ) {
            return;
          }

          state.language =
            lang;

          buttons.forEach(
            item => {

              item.classList.toggle(
                "active",
                item.dataset.lang === lang
              );

            }
          );

          /*
             Reload stories from API.

             This is important because the backend
             returns the requested language.
          */

          loadStories();
        }
      );

    }
  );
}


/* =========================================================
   CATEGORY BUTTONS
========================================================= */

function setupCategoryButtons() {

  document.addEventListener(
    "click",
    event => {

      const button =
        event.target.closest(
          "[data-category]"
        );

      if (!button) {
        return;
      }

      /*
        Ignore language buttons.
      */

      if (
        button.classList.contains(
          "language"
        )
      ) {
        return;
      }

      const category =
        button.dataset.category;

      if (!category) {
        return;
      }

      state.category =
        category;

      updateCategoryButtons();

      loadStories();

      window.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    }
  );
}


function updateCategoryButtons() {

  $$("[data-category]")
    .forEach(
      button => {

        if (
          button.classList.contains(
            "language"
          )
        ) {
          return;
        }

        const category =
          button.dataset.category;

        button.classList.toggle(
          "active",
          category === state.category
        );
      }
    );
}


/* =========================================================
   SEARCH
========================================================= */

function setupSearch() {

  const input =
    $("#searchInput");

  if (!input) {
    return;
  }

  let timer = null;

  input.addEventListener(
    "input",
    event => {

      clearTimeout(timer);

      state.search =
        cleanText(
          event.target.value
        );

      timer =
        setTimeout(
          () => {

            loadStories();

          },
          350
        );
    }
  );
}


/* =========================================================
   API
========================================================= */

async function fetchStories() {

  const params =
    new URLSearchParams();

  params.set(
    "lang",
    state.language
  );

  params.set(
    "category",
    state.category
  );

  if (state.search) {

    params.set(
      "q",
      state.search
    );
  }

  const response =
    await fetch(
      `${API_BASE}/stories?${params.toString()}`,
      {
        headers: {
          Accept:
            "application/json"
        }
      }
    );

  if (!response.ok) {

    throw new Error(
      `Unable to load stories (${response.status})`
    );
  }

  return response.json();
}


/* =========================================================
   LOAD STORIES
========================================================= */

async function loadStories() {

  if (state.loading) {
    return;
  }

  state.loading = true;

  showLoading();

  try {

    const data =
      await fetchStories();

    state.stories =
      Array.isArray(
        data.stories
      )
        ? data.stories
        : [];

    renderAll();

  } catch (error) {

    console.error(
      "Snippet24:",
      error
    );

    showError(
      "News could not be loaded. Please check that the server is running."
    );

  } finally {

    state.loading = false;
  }
}


/* =========================================================
   LOADING
========================================================= */

function showLoading() {

  const grid =
    $("#newsGrid");

  if (!grid) {
    return;
  }

  grid.innerHTML = `
    <div class="loading-state">
      <div class="loader"></div>
      <p>Loading the latest news…</p>
    </div>
  `;

  const hero =
    $("#heroStory");

  if (hero) {
    hero.innerHTML = "";
  }
}


/* =========================================================
   ERROR
========================================================= */

function showError(message) {

  const grid =
    $("#newsGrid");

  if (!grid) {
    return;
  }

  grid.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">⚠️</div>

      <h3>Unable to load news</h3>

      <p>
        ${escapeHTML(message)}
      </p>
    </div>
  `;
}


/* =========================================================
   RENDER EVERYTHING
========================================================= */

function renderAll() {

  renderStoryCount();

  renderHero();

  renderTrending();

  renderNewsGrid();

  renderLiveWire();

  updateSectionTitle();
}


/* =========================================================
   STORY COUNT
========================================================= */

function renderStoryCount() {

  const element =
    $("#storyCount");

  if (!element) {
    return;
  }

  const count =
    state.stories.length;

  element.textContent =
    `${count} ${count === 1 ? "story" : "stories"}`;
}


/* =========================================================
   SECTION TITLE
========================================================= */

function updateSectionTitle() {

  const title =
    $("#sectionTitle");

  if (!title) {
    return;
  }

  if (
    state.search
  ) {

    title.textContent =
      `Search Results for "${state.search}"`;

    return;
  }

  if (
    state.category === "all"
  ) {

    title.textContent =
      "Latest Stories";

    return;
  }

  title.textContent =
    state.category;
}


/* =========================================================
   HERO STORY
========================================================= */

function renderHero() {

  const container =
    $("#heroStory");

  if (!container) {
    return;
  }

  const story =
    state.stories[0];

  if (!story) {

    container.innerHTML = "";

    return;
  }

  const text =
    getStoryLanguage(
      story
    );

  const image =
    getImageUrl(
      story
    );

  const category =
    story.snippet24?.category ||
    "";

  const location =
    story.snippet24?.location ||
    "";

  const published =
    story.source?.publishedAt;

  container.innerHTML = `
    <article
      class="hero-card"
      data-story-id="${escapeHTML(story.id)}"
      tabindex="0"
      role="button"
      aria-label="Open story"
    >

      <div class="hero-card-image">

        <img
          src="${escapeHTML(image)}"
          alt="${escapeHTML(text.headline)}"
          loading="eager"
          onerror="this.src='/fallback-news.svg'"
        >

      </div>

      <div class="hero-card-content">

        <span class="story-category">
          ${escapeHTML(category)}
        </span>

        <h2>
          ${escapeHTML(text.headline)}
        </h2>

        <p class="hero-card-summary">
          ${escapeHTML(text.summary)}
        </p>

        <div class="hero-meta">

          ${
            location
              ? `<span>📍 ${escapeHTML(location)}</span>`
              : ""
          }

          ${
            published
              ? `<span>${escapeHTML(formatDate(published))}</span>`
              : ""
          }

          ${
            published
              ? `<span>${escapeHTML(formatTime(published))}</span>`
              : ""
          }

        </div>

        <div class="hero-read">
          Read full Snippet24 report →
        </div>

      </div>

    </article>
  `;

  attachStoryNavigation(
    container
  );
}


/* =========================================================
   NEWS GRID
========================================================= */

function renderNewsGrid() {

  const grid =
    $("#newsGrid");

  if (!grid) {
    return;
  }

  if (!state.stories.length) {

    grid.innerHTML = `
      <div class="empty-state">

        <div class="empty-icon">
          📰
        </div>

        <h3>
          No stories found
        </h3>

        <p>
          Try another category, language or search.
        </p>

      </div>
    `;

    return;
  }

  /*
    Do not display the hero story again
    in the normal grid.
  */

  const stories =
    state.stories.slice(1);

  if (!stories.length) {

    grid.innerHTML = "";

    return;
  }

  grid.innerHTML =
    stories
      .map(
        story =>
          createNewsCard(
            story
          )
      )
      .join("");

  attachStoryNavigation(
    grid
  );
}


/* =========================================================
   CREATE NEWS CARD
========================================================= */

function createNewsCard(story) {

  const text =
    getStoryLanguage(
      story
    );

  const image =
    getImageUrl(
      story
    );

  const category =
    story.snippet24?.category ||
    "";

  const location =
    story.snippet24?.location ||
    "";

  const source =
    story.source?.sourceName ||
    "";

  const published =
    story.source?.publishedAt;

  return `
    <article
      class="news-card"
      data-story-id="${escapeHTML(story.id)}"
      tabindex="0"
      role="button"
      aria-label="Open story"
    >

      <div class="news-image">

        <img
          src="${escapeHTML(image)}"
          alt="${escapeHTML(text.headline)}"
          loading="lazy"
          onerror="this.src='/fallback-news.svg'"
        >

        ${
          story.imageGenerated
            ? `
              <span class="image-label">
                AI Editorial Illustration
              </span>
            `
            : ""
        }

      </div>


      <div class="news-content">

        <span class="news-category">
          ${escapeHTML(category)}
        </span>


        <h3>
          ${escapeHTML(text.headline)}
        </h3>


        <p class="news-summary">
          ${escapeHTML(text.summary)}
        </p>


        <div class="news-meta">

          <span class="news-source">
            ${escapeHTML(source)}
          </span>

          <span class="news-location">

            ${
              location
                ? `📍 ${escapeHTML(location)}`
                : published
                  ? escapeHTML(
                      formatDate(
                        published
                      )
                    )
                  : ""
            }

          </span>

        </div>

      </div>

    </article>
  `;
}


/* =========================================================
   STORY NAVIGATION
========================================================= */

function attachStoryNavigation(
  container
) {

  const cards =
    container.querySelectorAll(
      "[data-story-id]"
    );

  cards.forEach(
    card => {

      card.addEventListener(
        "click",
        () => {

          const id =
            card.dataset.storyId;

          if (!id) {
            return;
          }

          openStory(
            id
          );
        }
      );


      card.addEventListener(
        "keydown",
        event => {

          if (
            event.key === "Enter" ||
            event.key === " "
          ) {

            event.preventDefault();

            const id =
              card.dataset.storyId;

            if (id) {
              openStory(id);
            }
          }
        }
      );

    }
  );
}


/* =========================================================
   OPEN STORY
========================================================= */

function openStory(id) {

  /*
    This opens OUR Snippet24 story page.

    It does NOT send the user directly to
    the source website.

    The Snippet24 story page can then show:

    - AI rewritten headline
    - AI summary
    - 3 key points
    - AI editorial image
    - date/time
    - location
    - source attribution
    - original source link
    - legal/media/copyright footnote
  */

  window.location.href =
    `/story?id=${encodeURIComponent(id)}`;
}


/* =========================================================
   IMAGE URL
========================================================= */

function getImageUrl(story) {

  if (
    story &&
    story.imageUrl
  ) {

    return story.imageUrl;
  }

  /*
    Do NOT reuse one random image for every story.

    If an AI image was not generated,
    use the neutral fallback.
  */

  return "/fallback-news.svg";
}


/* =========================================================
   TRENDING
========================================================= */

function renderTrending() {

  const container =
    $("#trending");

  if (!container) {
    return;
  }

  const stories =
    state.stories.slice(
      0,
      8
    );

  if (!stories.length) {

    container.innerHTML = "";

    return;
  }

  container.innerHTML =
    stories
      .map(
        (story, index) => {

          const text =
            getStoryLanguage(
              story
            );

          const location =
            story.snippet24?.location ||
            "";

          return `
            <article
              class="trending-card"
              data-story-id="${escapeHTML(story.id)}"
              tabindex="0"
              role="button"
            >

              <div class="trending-number">
                ${String(index + 1).padStart(2, "0")}
              </div>

              <h3>
                ${escapeHTML(text.headline)}
              </h3>

              <small>
                ${
                  location
                    ? `📍 ${escapeHTML(location)}`
                    : "Latest update"
                }
              </small>

            </article>
          `;
        }
      )
      .join("");

  attachStoryNavigation(
    container
  );
}


/* =========================================================
   LIVE WIRE
========================================================= */

function renderLiveWire() {

  const track =
    $("#tickerTrack");

  if (!track) {
    return;
  }

  const stories =
    state.stories.slice(
      0,
      15
    );

  if (!stories.length) {

    track.innerHTML =
      `
        <span class="ticker-item">
          Waiting for the latest news updates…
        </span>
      `;

    return;
  }

  const items =
    stories
      .map(
        story => {

          const text =
            getStoryLanguage(
              story
            );

          return `
            <span
              class="ticker-item"
            >
              ${escapeHTML(text.headline)}
            </span>
          `;
        }
      )
      .join("");

  /*
    Duplicate the ticker content so the
    walking/marquee effect remains continuous.
  */

  track.innerHTML =
    items + items;
}


/* =========================================================
   LIVE WIRE CLICK SUPPORT
========================================================= */

function setupTickerClicks() {

  const ticker =
    $("#tickerTrack");

  if (!ticker) {
    return;
  }

  ticker.addEventListener(
    "click",
    event => {

      const item =
        event.target.closest(
          ".ticker-item"
        );

      if (!item) {
        return;
      }

      /*
        Find matching headline.
      */

      const headline =
        item.textContent
          .trim();

      const story =
        state.stories.find(
          story => {

            const text =
              getStoryLanguage(
                story
              );

            return (
              text.headline ===
              headline
            );
          }
        );

      if (story) {

        openStory(
          story.id
        );
      }
    }
  );
}


/* =========================================================
   MOBILE CATEGORY DRAWER
========================================================= */

function setupMobileCategories() {

  const button =
    $("#mobileCategories");

  if (!button) {
    return;
  }

  button.addEventListener(
    "click",
    () => {

      openCategoryDrawer();

    }
  );
}


function openCategoryDrawer() {

  closeCategoryDrawer();

  const drawer =
    document.createElement(
      "div"
    );

  drawer.className =
    "category-drawer";

  drawer.id =
    "categoryDrawer";

  drawer.innerHTML = `
    <div
      class="category-drawer-inner"
      role="dialog"
      aria-modal="true"
    >

      <div class="drawer-header">

        <strong>
          Categories
        </strong>

        <button
          type="button"
          id="closeCategoryDrawer"
          aria-label="Close"
        >
          ×
        </button>

      </div>


      <div class="mobile-category-list">

        <button
          data-category="all"
          class="${state.category === "all" ? "active" : ""}"
        >
          ⌂ Home
        </button>

        ${CATEGORY_NAMES.map(
          category => `
            <button
              data-category="${escapeHTML(category)}"
              class="${state.category === category ? "active" : ""}"
            >
              ${escapeHTML(category)}
            </button>
          `
        ).join("")}

      </div>

    </div>
  `;

  document.body.appendChild(
    drawer
  );


  drawer
    .querySelector(
      "#closeCategoryDrawer"
    )
    ?.addEventListener(
      "click",
      closeCategoryDrawer
    );


  drawer.addEventListener(
    "click",
    event => {

      if (
        event.target ===
        drawer
      ) {

        closeCategoryDrawer();

        return;
      }

      const categoryButton =
        event.target.closest(
          "[data-category]"
        );

      if (
        !categoryButton
      ) {
        return;
      }

      state.category =
        categoryButton.dataset.category;

      updateCategoryButtons();

      closeCategoryDrawer();

      loadStories();

    }
  );
}


function closeCategoryDrawer() {

  const drawer =
    $("#categoryDrawer");

  if (drawer) {
    drawer.remove();
  }
}


/* =========================================================
   MOBILE NAV ACTIVE STATE
========================================================= */

function updateMobileNav() {

  const nav =
    $(".mobile-nav");

  if (!nav) {
    return;
  }

  nav
    .querySelectorAll(
      "button[data-category]"
    )
    .forEach(
      button => {

        button.classList.toggle(
          "active",
          button.dataset.category ===
            state.category
        );
      }
    );
}


/* =========================================================
   WEATHER / CITY
========================================================= */

function setupWeather() {

  const weather =
    $(".weather");

  if (!weather) {
    return;
  }

  /*
    We don't hard-code "India" as the city.

    First try browser geolocation.

    Then reverse geocode through OpenStreetMap.

    If permission is denied, we display
    "India" as a safe fallback.
  */

  weather.style.cursor =
    "pointer";

  weather.addEventListener(
    "click",
    requestLocation
  );

  requestLocation();
}


function requestLocation() {

  if (
    !navigator.geolocation
  ) {

    setWeatherFallback();

    return;
  }

  navigator.geolocation.getCurrentPosition(
    position => {

      const latitude =
        position.coords.latitude;

      const longitude =
        position.coords.longitude;

      getCityFromCoordinates(
        latitude,
        longitude
      );

    },
    () => {

      setWeatherFallback();

    },
    {
      enableHighAccuracy: false,

      timeout: 8000,

      maximumAge: 300000
    }
  );
}


async function getCityFromCoordinates(
  latitude,
  longitude
) {

  try {

    const url =
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`;

    const response =
      await fetch(
        url,
        {
          headers: {
            Accept:
              "application/json"
          }
        }
      );

    if (!response.ok) {
      throw new Error(
        "Location lookup failed"
      );
    }

    const data =
      await response.json();

    const address =
      data.address ||
      {};

    const city =
      address.city ||
      address.town ||
      address.municipality ||
      address.village ||
      address.county ||
      address.state ||
      "India";

    setWeatherCity(
      city
    );

    /*
      Weather API integration can be connected
      later. The city name is the important part
      for now.
    */

  } catch (error) {

    console.error(
      "Location:",
      error
    );

    setWeatherFallback();
  }
}


function setWeatherCity(
  city
) {

  const weather =
    $(".weather");

  if (!weather) {
    return;
  }

  weather.innerHTML = `
    <span>📍</span>

    <strong>
      ${escapeHTML(city)}
    </strong>

    <small>
      Your city
    </small>
  `;
}


function setWeatherFallback() {

  const weather =
    $(".weather");

  if (!weather) {
    return;
  }

  weather.innerHTML = `
    <span>📍</span>

    <strong>
      India
    </strong>

    <small>
      Location unavailable
    </small>
  `;
}


/* =========================================================
   KEYBOARD ESCAPE
========================================================= */

function setupEscapeKey() {

  document.addEventListener(
    "keydown",
    event => {

      if (
        event.key === "Escape"
      ) {

        closeCategoryDrawer();

      }
    }
  );
}


/* =========================================================
   PREVENT BROKEN IMAGE DISPLAY
========================================================= */

function setupImageFallback() {

  document.addEventListener(
    "error",
    event => {

      const image =
        event.target;

      if (
        image &&
        image.tagName ===
          "IMG"
      ) {

        if (
          image.dataset.fallbackApplied
        ) {
          return;
        }

        image.dataset.fallbackApplied =
          "true";

        image.src =
          "/fallback-news.svg";
      }

    },
    true
  );
}


/* =========================================================
   AUTO REFRESH
========================================================= */

function startAutoRefresh() {

  /*
    Refresh every 5 minutes.

    This allows new RSS-ingested stories
    to appear without manually refreshing
    the browser.

    The browser only reads /api/stories.

    RSS ingestion itself is performed by
    the backend /api/ingest.
  */

  setInterval(
    () => {

      if (
        document.visibilityState ===
        "visible"
      ) {

        loadStories();

      }

    },
    5 * 60 * 1000
  );
}


/* =========================================================
   INIT
========================================================= */

async function init() {

  console.log(
    "Snippet24 frontend starting…"
  );


  startClock();


  setupLanguageButtons();


  setupCategoryButtons();


  setupSearch();


  setupMobileCategories();


  setupEscapeKey();


  setupImageFallback();


  setupTickerClicks();


  setupWeather();


  updateCategoryButtons();


  updateMobileNav();


  await loadStories();


  startAutoRefresh();


  console.log(
    "Snippet24 frontend ready."
  );
}


/* =========================================================
   START APPLICATION
========================================================= */

if (
  document.readyState ===
  "loading"
) {

  document.addEventListener(
    "DOMContentLoaded",
    init
  );

} else {

  init();

}