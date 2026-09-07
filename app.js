(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  const STORAGE_KEY = "snippet24_location";

  const state = {
    location: null,
    stories: [],
    activeCategory: "all"
  };


  /* -----------------------------
     SAFE STORAGE
  ----------------------------- */

  function getSavedLocation() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;

      const parsed = JSON.parse(raw);

      if (!parsed || typeof parsed !== "object") {
        return null;
      }

      return parsed;
    } catch {
      return null;
    }
  }

  function saveLocation(location) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
    } catch {
      // Storage may be unavailable.
    }
  }


  /* -----------------------------
     SAFE TEXT
  ----------------------------- */

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }


  /* -----------------------------
     SAFE EXTERNAL URL
  ----------------------------- */

  function safeExternalUrl(value) {
    if (!value) return null;

    try {
      const url = new URL(String(value), window.location.href);

      if (
        url.protocol !== "https:" &&
        url.protocol !== "http:"
      ) {
        return null;
      }

      return url.href;
    } catch {
      return null;
    }
  }


  /* -----------------------------
     CATEGORY
  ----------------------------- */

  function normalizeCategory(story) {
    const raw = String(
      story.category ||
      story.section ||
      story.topic ||
      ""
    ).toLowerCase();

    if (
      raw.includes("business") ||
      raw.includes("econom") ||
      raw.includes("finance") ||
      raw.includes("money")
    ) {
      return "business";
    }

    if (
      raw.includes("tech") ||
      raw.includes("ai") ||
      raw.includes("science")
    ) {
      return "tech";
    }

    if (raw.includes("sport")) {
      return "sports";
    }

    if (
      raw.includes("people") ||
      raw.includes("culture") ||
      raw.includes("society")
    ) {
      return "people";
    }

    if (
      raw.includes("global") ||
      raw.includes("world") ||
      raw.includes("international")
    ) {
      return "global";
    }

    if (
      raw.includes("india") ||
      raw.includes("state") ||
      raw.includes("local")
    ) {
      return "india";
    }

    return "india";
  }


  /* -----------------------------
     STORY FIELDS
  ----------------------------- */

  function storyTitle(story) {
    return (
      story.headline ||
      story.title ||
      story.name ||
      "Untitled story"
    );
  }

  function storySummary(story) {
    return (
      story.summary ||
      story.description ||
      story.snippet ||
      story.excerpt ||
      ""
    );
  }

  function storySource(story) {
    return (
      story.source_name ||
      story.source ||
      story.publisher ||
      "Snippet24"
    );
  }

  function storyUrl(story) {
    return safeExternalUrl(
      story.url ||
      story.link ||
      story.source_url ||
      story.article_url
    );
  }


  /* -----------------------------
     LOAD STORIES
  ----------------------------- */

  async function fetchJson(url) {
    const response = await fetch(url, {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  async function loadStories() {

    let data = null;

    try {
      data = await fetchJson("./api/stories");
    } catch {
      try {
        data = await fetchJson("./articles.json");
      } catch {
        data = null;
      }
    }

    let stories = [];

    if (Array.isArray(data)) {
      stories = data;
    } else if (data && Array.isArray(data.articles)) {
      stories = data.articles;
    } else if (data && Array.isArray(data.stories)) {
      stories = data.stories;
    } else if (data && data.data && Array.isArray(data.data)) {
      stories = data.data;
    }

    state.stories = stories.filter(
      item => item && typeof item === "object"
    );

    renderStories();
    renderTicker();
    renderCounts();
  }


  /* -----------------------------
     RENDER TOP STORIES
  ----------------------------- */

  function createStoryCard(story) {

    const title = esc(storyTitle(story));
    const summary = esc(storySummary(story));
    const source = esc(storySource(story));
    const category = esc(
      story.category ||
      story.section ||
      normalizeCategory(story)
    );

    const url = storyUrl(story);

    return `
      <article class="story-card">

        <span class="story-category">
          ${category}
        </span>

        <h3>${title}</h3>

        <p>${summary}</p>

        <div class="story-source">
          Source: ${source}
        </div>

        ${
          url
            ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">READ SOURCE →</a>`
            : ""
        }

      </article>
    `;
  }


  function renderTopStories() {

    const container = $("#topStoriesGrid");

    if (!container) return;

    const stories = state.stories.slice(0, 6);

    if (!stories.length) {
      container.innerHTML = `
        <article class="waiting-card">
          <span>●</span>
          <h3>WAITING FOR SIGNAL</h3>
          <p>Latest stories will appear here when the news feed is available.</p>
        </article>
      `;
      return;
    }

    container.innerHTML = stories
      .map(createStoryCard)
      .join("");
  }


  /* -----------------------------
     MORE NEWS
  ----------------------------- */

  function renderMoreNews() {

    const container = $("#moreNewsGrid");

    if (!container) return;

    let stories = state.stories;

    if (state.activeCategory !== "all") {
      stories = stories.filter(
        story => normalizeCategory(story) === state.activeCategory
      );
    }

    stories = stories.slice(0, 18);

    if (!stories.length) {
      container.innerHTML = `
        <p class="empty-state">
          No stories found for this section yet.
        </p>
      `;
      return;
    }

    container.innerHTML = stories
      .map(story => {

        const title = esc(storyTitle(story));
        const summary = esc(storySummary(story));
        const category = esc(
          story.category ||
          story.section ||
          normalizeCategory(story)
        );

        const url = storyUrl(story);

        return `
          <article class="more-story">

            <span class="story-category">
              ${category}
            </span>

            <h3>${title}</h3>

            <p>${summary}</p>

            ${
              url
                ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">READ →</a>`
                : ""
            }

          </article>
        `;
      })
      .join("");
  }


  function renderStories() {
    renderTopStories();
    renderMoreNews();
  }


  /* -----------------------------
     LIVE TICKER
  ----------------------------- */

  function renderTicker() {

    const ticker = $("#liveTicker");

    if (!ticker) return;

    const stories = state.stories.slice(0, 8);

    if (!stories.length) {
      ticker.innerHTML = `
        <span>Snippet24 Live Wire — waiting for the latest updates…</span>
      `;
      return;
    }

    ticker.innerHTML = stories
      .map(
        story =>
          `<span>${esc(storyTitle(story))}</span>`
      )
      .join("");
  }


  /* -----------------------------
     LOCATION
  ----------------------------- */

  async function detectLocation() {

    const place = $("#weatherPlace");

    if (place) {
      place.textContent = "Detecting area…";
    }

    try {

      const response = await fetch(
        "https://ipapi.co/json/",
        {
          cache: "no-store"
        }
      );

      if (!response.ok) {
        throw new Error("Location service unavailable");
      }

      const data = await response.json();

      const latitude = Number(data.latitude);
      const longitude = Number(data.longitude);

      if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude)
      ) {
        throw new Error("Invalid coordinates");
      }

      const location = {
        city:
          data.city ||
          data.town ||
          data.village ||
          "",

        district:
          data.district ||
          "",

        state:
          data.region ||
          data.state ||
          "",

        country:
          data.country_name ||
          "India",

        latitude,
        longitude,

        source: "ip"
      };

      state.location = location;
      saveLocation(location);

      await enrichLocation();

      updateLocationUI();
      await updateWeather();
      renderCounts();

    } catch {

      if (place) {
        place.textContent = "Location unavailable";
      }

      updateLocationUI();
      renderCounts();
    }
  }


  async function enrichLocation() {

    if (
      !state.location ||
      !Number.isFinite(state.location.latitude) ||
      !Number.isFinite(state.location.longitude)
    ) {
      return;
    }

    try {

      const url =
        "https://api.bigdatacloud.net/data/reverse-geocode-client" +
        `?latitude=${encodeURIComponent(state.location.latitude)}` +
        `&longitude=${encodeURIComponent(state.location.longitude)}` +
        "&localityLanguage=en";

      const response = await fetch(url, {
        cache: "no-store"
      });

      if (!response.ok) return;

      const data = await response.json();

      const city =
        data.city ||
        data.locality ||
        data.principalSubdivision ||
        "";

      const district =
        data.localityInfo?.administrativeArea?.find(
          item =>
            String(item.name || "")
              .toLowerCase()
              .includes("district")
        )?.name ||
        data.principalSubdivision ||
        state.location.district ||
        "";

      const stateName =
        data.principalSubdivision ||
        state.location.state ||
        "";

      if (city) state.location.city = city;
      if (district) state.location.district = district;
      if (stateName) state.location.state = stateName;

      saveLocation(state.location);

    } catch {
      // Approximate IP location remains usable.
    }
  }


  function updateLocationUI() {

    const location = state.location;

    const place = $("#weatherPlace");

    if (!place) return;

    if (!location) {
      place.textContent = "Detecting area…";
      return;
    }

    const name =
      location.city ||
      location.district ||
      location.state ||
      "Your area";

    place.textContent = name;
  }


  /* -----------------------------
     WEATHER
  ----------------------------- */

  function weatherDescription(code) {

    const map = {
      0: ["☀", "Clear"],
      1: ["🌤", "Mainly clear"],
      2: ["⛅", "Partly cloudy"],
      3: ["☁", "Cloudy"],
      45: ["🌫", "Fog"],
      48: ["🌫", "Fog"],
      51: ["🌦", "Drizzle"],
      53: ["🌦", "Drizzle"],
      55: ["🌧", "Drizzle"],
      61: ["🌧", "Rain"],
      63: ["🌧", "Rain"],
      65: ["🌧", "Heavy rain"],
      71: ["🌨", "Snow"],
      73: ["🌨", "Snow"],
      75: ["❄", "Snow"],
      80: ["🌦", "Showers"],
      81: ["🌦", "Showers"],
      82: ["⛈", "Heavy showers"],
      95: ["⛈", "Thunderstorm"],
      96: ["⛈", "Thunderstorm"],
      99: ["⛈", "Thunderstorm"]
    };

    return map[code] || ["☁", "Weather"];
  }


  async function updateWeather() {

    if (!state.location) return;

    const lat = Number(state.location.latitude);
    const lon = Number(state.location.longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      return;
    }

    try {

      const url =
        "https://api.open-meteo.com/v1/forecast" +
        `?latitude=${encodeURIComponent(lat)}` +
        `&longitude=${encodeURIComponent(lon)}` +
        "&current=temperature_2m,weather_code" +
        "&timezone=auto" +
        "&forecast_days=1";

      const response = await fetch(url, {
        cache: "no-store"
      });

      if (!response.ok) {
        throw new Error("Weather unavailable");
      }

      const data = await response.json();

      const temperature =
        data.current?.temperature_2m;

      const code =
        data.current?.weather_code;

      if (
        Number.isFinite(Number(temperature))
      ) {
        $("#weatherTemp").textContent =
          `${Math.round(Number(temperature))}°`;
      }

      const [icon] = weatherDescription(code);

      $("#weatherIcon").textContent = icon;

    } catch {
      $("#weatherTemp").textContent = "--°";
    }
  }


  /* -----------------------------
     LOCAL COUNTS
  ----------------------------- */

  function renderCounts() {

    const near = $("#nearCount");
    const district = $("#districtCount");
    const stateCount = $("#stateCount");

    const location = state.location;

    if (!location) {
      if (near) near.textContent = "—";
      if (district) district.textContent = "—";
      if (stateCount) stateCount.textContent = "—";
      return;
    }

    const city =
      String(location.city || "").toLowerCase();

    const districtName =
      String(location.district || "").toLowerCase();

    const stateName =
      String(location.state || "").toLowerCase();

    const localStories = state.stories.filter(story => {

      const text = [
        storyTitle(story),
        storySummary(story),
        story.location,
        story.city,
        story.district,
        story.state
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return (
        (city && text.includes(city)) ||
        (districtName && text.includes(districtName)) ||
        (stateName && text.includes(stateName))
      );
    });

    const districtStories = state.stories.filter(story => {

      const text = [
        storyTitle(story),
        storySummary(story),
        story.location,
        story.district,
        story.state
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return (
        districtName &&
        text.includes(districtName)
      );
    });

    const stateStories = state.stories.filter(story => {

      const text = [
        storyTitle(story),
        storySummary(story),
        story.location,
        story.state
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return (
        stateName &&
        text.includes(stateName)
      );
    });

    if (near) {
      near.textContent = localStories.length;
    }

    if (district) {
      district.textContent = districtStories.length;
    }

    if (stateCount) {
      stateCount.textContent = stateStories.length;
    }
  }


  /* -----------------------------
     LOCAL FILTER
  ----------------------------- */

  function showLocalStories(type) {

    let location = state.location;

    if (!location) {
      openLocationModal();
      return;
    }

    const city =
      String(location.city || "").toLowerCase();

    const district =
      String(location.district || "").toLowerCase();

    const stateName =
      String(location.state || "").toLowerCase();

    let stories = [];

    if (type === "near") {

      stories = state.stories.filter(story => {

        const text = [
          storyTitle(story),
          storySummary(story),
          story.location,
          story.city,
          story.district
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return city && text.includes(city);
      });

    } else if (type === "district") {

      stories = state.stories.filter(story => {

        const text = [
          storyTitle(story),
          storySummary(story),
          story.location,
          story.district
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return district && text.includes(district);
      });

    } else if (type === "state") {

      stories = state.stories.filter(story => {

        const text = [
          storyTitle(story),
          storySummary(story),
          story.location,
          story.state
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return stateName && text.includes(stateName);
      });
    }

    const target =
      $("#moreNewsGrid");

    if (!target) return;

    if (!stories.length) {

      target.innerHTML = `
        <p class="empty-state">
          No local stories found yet.
        </p>
      `;

    } else {

      target.innerHTML =
        stories
          .slice(0, 18)
          .map(story => {

            const url = storyUrl(story);

            return `
              <article class="more-story">

                <span class="story-category">
                  LOCAL
                </span>

                <h3>
                  ${esc(storyTitle(story))}
                </h3>

                <p>
                  ${esc(storySummary(story))}
                </p>

                ${
                  url
                    ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">READ →</a>`
                    : ""
                }

              </article>
            `;
          })
          .join("");
    }

    document
      .querySelector("#more")
      ?.scrollIntoView({
        behavior: "smooth"
      });
  }


  /* -----------------------------
     LOCATION MODAL
  ----------------------------- */

  function openLocationModal() {

    const modal = $("#locationOverlay");

    if (!modal) return;

    const location = state.location;

    if (location) {
      $("#manualState").value =
        location.state || "";

      $("#manualDistrict").value =
        location.district || "";

      $("#manualCity").value =
        location.city || "";
    }

    modal.hidden = false;
  }


  function closeLocationModal() {

    const modal = $("#locationOverlay");

    if (modal) {
      modal.hidden = true;
    }
  }


  function saveManualLocation() {

    const location = {

      state:
        $("#manualState").value.trim(),

      district:
        $("#manualDistrict").value.trim(),

      city:
        $("#manualCity").value.trim(),

      taluk:
        $("#manualTaluk").value.trim(),

      locality:
        $("#manualLocality").value.trim(),

      source: "manual"
    };

    if (
      !location.state &&
      !location.district &&
      !location.city
    ) {
      return;
    }

    state.location = location;

    saveLocation(location);

    updateLocationUI();
    renderCounts();
    closeLocationModal();
  }


  /* -----------------------------
     SEARCH
  ----------------------------- */

  function openSearch() {

    const overlay = $("#searchOverlay");

    if (!overlay) return;

    overlay.hidden = false;

    setTimeout(() => {
      $("#searchInput")?.focus();
    }, 50);
  }


  function closeSearch() {

    const overlay = $("#searchOverlay");

    if (overlay) {
      overlay.hidden = true;
    }
  }


  function performSearch(query) {

    const results = $("#searchResults");

    if (!results) return;

    const q = query.trim().toLowerCase();

    if (!q) {
      results.innerHTML = "";
      return;
    }

    const matches = state.stories
      .filter(story => {

        const text = [
          storyTitle(story),
          storySummary(story),
          story.category,
          story.location,
          story.city,
          story.state
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        return text.includes(q);
      })
      .slice(0, 10);

    if (!matches.length) {

      results.innerHTML = `
        <p class="empty-state">
          No stories found for “${esc(query)}”.
        </p>
      `;

      return;
    }

    results.innerHTML = matches
      .map(story => {

        const url = storyUrl(story);

        return `
          <div class="search-result">

            <small>
              ${esc(storySource(story))}
            </small>

            <h3>
              ${esc(storyTitle(story))}
            </h3>

            <p>
              ${esc(storySummary(story))}
            </p>

            ${
              url
                ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">READ SOURCE →</a>`
                : ""
            }

          </div>
        `;
      })
      .join("");
  }


  /* -----------------------------
     CATCH ME UP
  ----------------------------- */

  function catchMeUp() {

    const top =
      $("#topStories");

    if (!top) return;

    top.scrollIntoView({
      behavior: "smooth"
    });
  }


  /* -----------------------------
     EVENTS
  ----------------------------- */

  function bindEvents() {

    $("#searchBtn")?.addEventListener(
      "click",
      openSearch
    );

    $("#closeSearch")?.addEventListener(
      "click",
      closeSearch
    );

    $("#searchOverlay")?.addEventListener(
      "click",
      event => {
        if (event.target.id === "searchOverlay") {
          closeSearch();
        }
      }
    );

    $("#searchForm")?.addEventListener(
      "submit",
      event => {
        event.preventDefault();
        performSearch($("#searchInput").value);
      }
    );

    $("#searchInput")?.addEventListener(
      "input",
      event => {
        performSearch(event.target.value);
      }
    );


    $("#changeLocation")?.addEventListener(
      "click",
      openLocationModal
    );

    $("#closeLocation")?.addEventListener(
      "click",
      closeLocationModal
    );

    $("#locationOverlay")?.addEventListener(
      "click",
      event => {
        if (event.target.id === "locationOverlay") {
          closeLocationModal();
        }
      }
    );

    $("#saveLocation")?.addEventListener(
      "click",
      saveManualLocation
    );

    $("#detectAutomatic")?.addEventListener(
      "click",
      async () => {
        closeLocationModal();
        await detectLocation();
      }
    );


    $("#catchUpBtn")?.addEventListener(
      "click",
      catchMeUp
    );


    $("#nearCard")?.addEventListener(
      "click",
      () => showLocalStories("near")
    );

    $("#districtCard")?.addEventListener(
      "click",
      () => showLocalStories("district")
    );

    $("#stateCard")?.addEventListener(
      "click",
      () => showLocalStories("state")
    );

    $("#worldArrow")?.addEventListener(
      "click",
      () => showLocalStories("near")
    );


    $$(".category-tab").forEach(button => {

      button.addEventListener(
        "click",
        () => {

          $$(".category-tab").forEach(
            item => item.classList.remove("active")
          );

          button.classList.add("active");

          state.activeCategory =
            button.dataset.category || "all";

          renderMoreNews();
        }
      );

    });


    $("#menuBtn")?.addEventListener(
      "click",
      () => {
        $("#mainNav")?.scrollIntoView({
          behavior: "smooth"
        });
      }
    );


    document.addEventListener(
      "keydown",
      event => {

        if (event.key === "Escape") {
          closeSearch();
          closeLocationModal();
        }

      }
    );
  }


  /* -----------------------------
     START
  ----------------------------- */

  async function init() {

    bindEvents();

    /*
      IMPORTANT:
      No navigator.geolocation is used.
      No browser location permission is requested.
    */

    state.location = getSavedLocation();

    if (state.location) {
      updateLocationUI();
      updateWeather();
      renderCounts();
    } else {
      detectLocation();
    }

    await loadStories();
  }


  init();

})();