(() => {
  "use strict";

  /*
   * SNIPPET24 — PRODUCTION FRONTEND
   *
   * Important:
   * - NEVER requests browser GPS permission.
   * - Uses silent IP-based approximate location.
   * - AROUND YOU = Near You / District / State only.
   * - India / Global remain in the main navigation.
   * - No language selector dependency.
   * - External URLs are validated before being rendered.
   */

  const state = {
    stories: [],
    category: "All",
    speed: 10,
    location: null
  };

  const $ = (selector) =>
    document.querySelector(selector);

  const $$ = (selector) =>
    [...document.querySelectorAll(selector)];


  /* =========================================================
     SAFE HELPERS
  ========================================================= */

  const esc = (value) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (char) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        })[char]
    );


  function safeUrl(value) {
    if (!value) return "";

    try {
      const url = new URL(
        String(value),
        window.location.origin
      );

      if (
        url.protocol !== "https:" &&
        url.protocol !== "http:"
      ) {
        return "";
      }

      return url.href;

    } catch (_) {
      return "";
    }
  }


  function safeImageUrl(value) {
    const url = safeUrl(value);

    if (!url) return "";

    return url;
  }


  function formatDate(value) {
    const time = Date.parse(value || "");

    if (!Number.isFinite(time)) {
      return "";
    }

    return new Date(time).toLocaleDateString(
      undefined,
      {
        day: "numeric",
        month: "short",
        year: "numeric"
      }
    );
  }


  /* =========================================================
     STORY HELPERS
  ========================================================= */

  function titleOf(story) {
    return (
      story?.translations?.en?.title ||
      story?.en?.title ||
      story?.title ||
      story?.headline ||
      ""
    );
  }


  function summaryOf(story) {
    return (
      story?.translations?.en?.summary ||
      story?.en?.summary ||
      story?.summary ||
      ""
    );
  }


  function pointsOf(story) {
    const points =
      story?.translations?.en?.key_points ||
      story?.en?.key_points ||
      story?.key_points ||
      story?.snippet_lines ||
      [];

    return Array.isArray(points)
      ? points
      : [];
  }


  function imageOf(story) {
    return (
      story?.ai_image_url ||
      story?.image ||
      story?.image_url ||
      story?.ai_image ||
      ""
    );
  }


  function sourceOf(story) {
    return (
      story?.source_url ||
      story?.original_source_url ||
      story?.original_url ||
      story?.url ||
      ""
    );
  }


  function categoryOf(story) {
    const raw =
      story?.category ||
      story?.section ||
      "India";

    if (raw === "In India") {
      return "India";
    }

    return raw;
  }


  function importanceScore(story) {
    const map = {
      CRITICAL: 80,
      HIGH: 50,
      MEDIUM: 20,
      LOW: 5
    };

    return (
      map[
        String(
          story?.importance || ""
        ).toUpperCase()
      ] || 10
    );
  }


  function freshnessScore(story) {
    const time = Date.parse(
      story?.published_at ||
      story?.updated_at ||
      ""
    );

    if (!Number.isFinite(time)) {
      return 0;
    }

    const hours =
      (Date.now() - time) /
      3600000;

    return Math.max(
      0,
      40 - hours
    );
  }


  /* =========================================================
     LOCATION
  ========================================================= */

  function loadSavedLocation() {
    try {
      const saved =
        localStorage.getItem(
          "snippet24_location"
        );

      if (!saved) {
        return null;
      }

      const parsed =
        JSON.parse(saved);

      if (
        parsed &&
        typeof parsed === "object"
      ) {
        return parsed;
      }

    } catch (_) {}

    return null;
  }


  function saveLocation(location) {
    state.location = location;

    try {
      localStorage.setItem(
        "snippet24_location",
        JSON.stringify(location)
      );
    } catch (_) {}
  }


  function storyLocation(story) {
    const location =
      story?.location ||
      story?.geo ||
      {};

    return {
      country: String(
        location.country || ""
      ).toLowerCase(),

      state: String(
        location.state || ""
      ).toLowerCase(),

      district: String(
        location.district || ""
      ).toLowerCase(),

      city: String(
        location.city ||
        location.town ||
        ""
      ).toLowerCase(),

      taluk: String(
        location.taluk ||
        location.block ||
        ""
      ).toLowerCase(),

      locality: String(
        location.locality ||
        location.village ||
        location.ward ||
        ""
      ).toLowerCase()
    };
  }


  function locationScore(story) {
    const current =
      state.location;

    if (!current) {
      return 0;
    }

    const storyLoc =
      storyLocation(story);

    const currentLoc = {
      country: String(
        current.country || ""
      ).toLowerCase(),

      state: String(
        current.state || ""
      ).toLowerCase(),

      district: String(
        current.district || ""
      ).toLowerCase(),

      city: String(
        current.city || ""
      ).toLowerCase(),

      taluk: String(
        current.taluk || ""
      ).toLowerCase(),

      locality: String(
        current.locality || ""
      ).toLowerCase()
    };

    let score = 0;


    if (
      currentLoc.locality &&
      storyLoc.locality &&
      currentLoc.locality ===
      storyLoc.locality
    ) {
      score += 120;
    }


    if (
      currentLoc.taluk &&
      storyLoc.taluk &&
      currentLoc.taluk ===
      storyLoc.taluk
    ) {
      score += 95;
    }


    if (
      currentLoc.city &&
      storyLoc.city &&
      currentLoc.city ===
      storyLoc.city
    ) {
      score += 75;
    }


    if (
      currentLoc.district &&
      storyLoc.district &&
      currentLoc.district ===
      storyLoc.district
    ) {
      score += 55;
    }


    if (
      currentLoc.state &&
      storyLoc.state &&
      currentLoc.state ===
      storyLoc.state
    ) {
      score += 30;
    }


    return score;
  }


  /*
   * We deliberately DO NOT use:
   *
   * navigator.geolocation
   *
   * This prevents the browser from asking:
   * "Allow Snippet24 to use your location?"
   */


  async function detectLocation() {

    setWeatherDisplay(
      "--°",
      "Finding your area",
      "Detecting automatically…",
      "📍"
    );


    try {

      const response =
        await fetch(
          "https://ipapi.co/json/",
          {
            cache: "no-store"
          }
        );


      if (!response.ok) {
        throw new Error(
          "Location service unavailable"
        );
      }


      const data =
        await response.json();


      const latitude =
        Number(data.latitude);

      const longitude =
        Number(data.longitude);


      if (
        !data.city &&
        !data.region
      ) {
        throw new Error(
          "Location name unavailable"
        );
      }


      let location = {

        country:
          data.country_name ||
          data.country ||
          "",

        state:
          data.region ||
          "",

        district:
          "",

        city:
          data.city ||
          "",

        taluk:
          "",

        locality:
          data.city ||
          "",

        lat:
          Number.isFinite(latitude)
            ? latitude
            : null,

        lon:
          Number.isFinite(longitude)
            ? longitude
            : null,

        source:
          "ip"

      };


      /*
       * Try to improve district/local
       * information using the approximate
       * IP coordinates.
       *
       * This is still completely silent.
       */

      if (
        Number.isFinite(latitude) &&
        Number.isFinite(longitude)
      ) {

        try {

          const reverse =
            await reverseGeocode(
              latitude,
              longitude
            );


          location = {
            ...location,
            ...reverse,
            lat: latitude,
            lon: longitude,
            source: "ip"
          };

        } catch (_) {

          /*
           * IP city/state information
           * remains valid if reverse
           * geocoding fails.
           */

        }

      }


      saveLocation(location);

      await updateWeather();

      render();

    } catch (_) {

      setWeatherDisplay(
        "--°",
        "Location unavailable",
        "Weather unavailable",
        "📍"
      );

      renderCounts();

    }

  }


  async function reverseGeocode(
    latitude,
    longitude
  ) {

    const url =
      "https://api.bigdatacloud.net/data/" +
      "reverse-geocode-client" +
      `?latitude=${encodeURIComponent(latitude)}` +
      `&longitude=${encodeURIComponent(longitude)}` +
      "&localityLanguage=en";


    const response =
      await fetch(
        url,
        {
          cache: "no-store"
        }
      );


    if (!response.ok) {
      throw new Error(
        "Reverse geocoding failed"
      );
    }


    const data =
      await response.json();


    const address =
      data.address || {};


    const admin =
      data.localityInfo?.administrative ||
      [];


    const district =
      admin.find(
        item =>
          /district/i.test(
            item.description || ""
          )
      );


    return {

      country:
        address.countryName ||
        data.countryName ||
        "",

      state:
        address.principalSubdivision ||
        "",

      district:
        district?.name ||
        "",

      city:
        address.city ||
        address.town ||
        address.village ||
        address.locality ||
        "",

      taluk:
        address.municipality ||
        address.suburb ||
        "",

      locality:
        address.village ||
        address.locality ||
        address.city ||
        address.town ||
        ""

    };

  }


  /* =========================================================
     WEATHER
  ========================================================= */

  function weatherDescription(code) {

    const value =
      Number(code);


    if (value === 0) {
      return [
        "☀️",
        "Clear"
      ];
    }


    if (
      [1, 2].includes(value)
    ) {
      return [
        "🌤️",
        "Partly cloudy"
      ];
    }


    if (value === 3) {
      return [
        "☁️",
        "Cloudy"
      ];
    }


    if (
      [45, 48].includes(value)
    ) {
      return [
        "🌫️",
        "Foggy"
      ];
    }


    if (
      [51, 53, 55, 56, 57].includes(value)
    ) {
      return [
        "🌦️",
        "Drizzle"
      ];
    }


    if (
      [61, 63, 65, 66, 67].includes(value)
    ) {
      return [
        "🌧️",
        "Rain"
      ];
    }


    if (
      [71, 73, 75, 77].includes(value)
    ) {
      return [
        "❄️",
        "Snow"
      ];
    }


    if (
      [80, 81, 82].includes(value)
    ) {
      return [
        "🌦️",
        "Showers"
      ];
    }


    if (
      [95, 96, 99].includes(value)
    ) {
      return [
        "⛈️",
        "Thunderstorm"
      ];
    }


    return [
      "🌤️",
      "Weather"
    ];

  }


  function setWeatherDisplay(
    temperature,
    location,
    condition,
    icon
  ) {

    const temp =
      $("#weatherTemp");

    const place =
      $("#weatherLocation");

    const description =
      $("#weatherCondition");

    const weatherIcon =
      $("#weatherIcon");


    if (temp) {
      temp.textContent =
        temperature;
    }


    if (place) {
      place.textContent =
        location;
    }


    if (description) {
      description.textContent =
        condition;
    }


    if (weatherIcon) {
      weatherIcon.textContent =
        icon;
    }

  }


  async function updateWeather() {

    const location =
      state.location;


    if (!location) {

      setWeatherDisplay(
        "--°",
        "Finding your area",
        "Weather updating…",
        "📍"
      );

      return;

    }


    const place =
      location.city ||
      location.locality ||
      location.district ||
      location.state ||
      "Your area";


    if (
      !Number.isFinite(
        Number(location.lat)
      ) ||
      !Number.isFinite(
        Number(location.lon)
      )
    ) {

      setWeatherDisplay(
        "--°",
        place,
        "Weather unavailable",
        "📍"
      );

      return;

    }


    try {

      const url =
        "https://api.open-meteo.com/v1/forecast" +
        `?latitude=${encodeURIComponent(location.lat)}` +
        `&longitude=${encodeURIComponent(location.lon)}` +
        "&current=temperature_2m,weather_code" +
        "&timezone=auto" +
        "&forecast_days=1";


      const response =
        await fetch(
          url,
          {
            cache: "no-store"
          }
        );


      if (!response.ok) {
        throw new Error(
          "Weather unavailable"
        );
      }


      const data =
        await response.json();


      const temperature =
        Number(
          data.current?.temperature_2m
        );


      const weatherCode =
        Number(
          data.current?.weather_code
        );


      const [
        icon,
        condition
      ] =
        weatherDescription(
          weatherCode
        );


      setWeatherDisplay(

        Number.isFinite(temperature)
          ? `${Math.round(temperature)}°`
          : "--°",

        place,

        condition,

        icon

      );

    } catch (_) {

      setWeatherDisplay(
        "--°",
        place,
        "Weather unavailable",
        "📍"
      );

    }

  }


  /* =========================================================
     NEWS FEED
  ========================================================= */

  async function loadStories() {

    setStatus(
      "Finding the signal…"
    );


    let data = null;


    /*
     * First try API.
     */

    try {

      const response =
        await fetch(
          "./api/stories",
          {
            cache: "no-store"
          }
        );


      if (response.ok) {
        data =
          await response.json();
      }

    } catch (_) {}


    /*
     * GitHub Pages / static fallback.
     */

    if (!data) {

      try {

        const response =
          await fetch(
            "./articles.json",
            {
              cache: "no-store"
            }
          );


        if (response.ok) {
          data =
            await response.json();
        }

      } catch (_) {}

    }


    if (Array.isArray(data)) {

      state.stories =
        data;

    } else if (
      Array.isArray(data?.stories)
    ) {

      state.stories =
        data.stories;

    } else if (
      Array.isArray(data?.articles)
    ) {

      state.stories =
        data.articles;

    } else {

      state.stories =
        [];

    }


    render();

  }


  function filteredStories() {

    return state.stories

      .filter(
        story =>
          titleOf(story)
      )

      .filter(
        story =>
          state.category === "All" ||
          categoryOf(story) ===
          state.category
      )

      .sort(
        (a, b) =>
          (
            locationScore(b) +
            importanceScore(b) +
            freshnessScore(b)
          ) -
          (
            locationScore(a) +
            importanceScore(a) +
            freshnessScore(a)
          )
      );

  }


  /* =========================================================
     RENDER
  ========================================================= */

  function setStatus(text) {

    const element =
      $("#status");

    if (element) {
      element.textContent =
        text;
    }

  }


  function render() {

    const stories =
      filteredStories();


    renderHeroStories(
      stories
    );


    renderMoreStories(
      stories
    );


    renderTicker(
      stories
    );


    renderCounts();

    syncControls();


    setStatus(
      stories.length
        ? `${stories.length} stories • updated now`
        : "No published stories available yet."
    );

  }


  function renderHeroStories(stories) {

    const container =
      $("#topStories");


    if (!container) {
      return;
    }


    const first =
      stories[0];


    const rest =
      stories.slice(1, 4);


    if (!first) {

      container.innerHTML = `

        <article class="lead-story">

          <div class="lead-copy">

            <span class="signal">
              WAITING FOR SIGNAL
            </span>

            <h3>
              Your most important stories will appear here.
            </h3>

            <p>
              The Snippet24 news feed is waiting for published stories.
            </p>

          </div>

        </article>

      `;

      return;

    }


    const image =
      safeImageUrl(
        imageOf(first)
      );


    const imageHTML =
      image
        ? `
          <img
            src="${esc(image)}"
            alt=""
            loading="eager"
            onerror="this.remove()"
          >
        `
        : "";


    const source =
      safeUrl(
        sourceOf(first)
      );


    const points =
      pointsOf(first)
        .slice(0, 3)
        .map(
          item =>
            esc(item)
        )
        .join(" • ");


    const date =
      formatDate(
        first.published_at ||
        first.updated_at
      );


    container.innerHTML = `

      <article class="lead-story">

        ${imageHTML}

        <div class="shade"></div>

        <div class="lead-copy">

          <span class="signal">
            ${esc(
              first.signal ||
              "TOP SIGNAL"
            )}
          </span>

          <h3>
            ${esc(
              titleOf(first)
            )}
          </h3>

          <p>
            ${esc(
              summaryOf(first) ||
              points ||
              "The latest important development, explained simply."
            )}
          </p>

          <div class="lead-meta">

            ${esc(
              categoryOf(first)
            )}

            ${
              date
                ? ` • ${esc(date)}`
                : ""
            }

            ${
              source
                ? " • Verified source"
                : ""
            }

          </div>

        </div>

      </article>


      <div class="side-stories">

        ${
          rest.length
            ? rest
                .map(
                  story =>
                    renderSideCard(
                      story
                    )
                )
                .join("")

            : `

              <div class="side-card">

                <div></div>

                <div>

                  <h3>
                    More important stories will appear here.
                  </h3>

                  <small>
                    FAST NEWS • REAL IMPACT
                  </small>

                </div>

              </div>

            `
        }

      </div>

    `;

  }


  function renderSideCard(story) {

    const image =
      safeImageUrl(
        imageOf(story)
      );


    return `

      <article class="side-card">

        ${
          image
            ? `
              <img
                src="${esc(image)}"
                alt=""
                loading="lazy"
                onerror="this.style.visibility='hidden'"
              >
            `
            : `
              <div></div>
            `
        }

        <div>

          <span class="signal">
            ${esc(
              story.signal ||
              categoryOf(story)
            )}
          </span>

          <h3>
            ${esc(
              titleOf(story)
            )}
          </h3>

          <small>
            ${esc(
              categoryOf(story)
            )}
          </small>

        </div>

      </article>

    `;

  }


  function renderMoreStories(stories) {

    const container =
      $("#stories");


    if (!container) {
      return;
    }


    const items =
      stories.slice(0, 10);


    if (!items.length) {

      container.innerHTML = `

        <div class="story-row">

          <div></div>

          <div>

            <h3>
              No stories found yet.
            </h3>

            <p>
              Connect the Snippet24 news feed to start publishing.
            </p>

          </div>

          <span class="go">
            ›
          </span>

        </div>

      `;

      return;

    }


    container.innerHTML =
      items
        .map(
          story =>
            renderStoryRow(
              story
            )
        )
        .join("");

  }


  function renderStoryRow(story) {

    const image =
      safeImageUrl(
        imageOf(story)
      );


    const source =
      safeUrl(
        sourceOf(story)
      );


    const body = `

      ${
        image

          ? `
            <img
              src="${esc(image)}"
              alt=""
              loading="lazy"
              onerror="this.style.visibility='hidden'"
            >
          `

          : `
            <img
              src=""
              alt=""
              aria-hidden="true"
            >
          `
      }


      <div>

        <h3>
          ${esc(
            titleOf(story)
          )}
        </h3>

        <p>
          ${esc(
            summaryOf(story) ||
            pointsOf(story)[0] ||
            "Understand what happened and why it matters."
          )}
        </p>

      </div>


      <span class="go">
        ›
      </span>

    `;


    if (source) {

      return `

        <a
          class="story-row"
          href="${esc(source)}"
          target="_blank"
          rel="noopener noreferrer nofollow"
        >

          ${body}

        </a>

      `;

    }


    return `

      <div class="story-row">

        ${body}

      </div>

    `;

  }


  function renderTicker(stories) {

    const element =
      $("#tickerTrack");


    if (!element) {
      return;
    }


    const items =
      stories.slice(0, 10);


    if (!items.length) {

      element.innerHTML = `

        <span>

          <strong>
            LIVE
          </strong>

          Waiting for the latest Snippet24 signal…

        </span>

      `;

      return;

    }


    const line =
      items
        .map(
          story =>
            `

              <span>

                <strong>
                  ●
                </strong>

                ${esc(
                  titleOf(story)
                )}

              </span>

            `
        )
        .join("");


    element.innerHTML =
      line + line;

  }


  /* =========================================================
     AROUND YOU
  ========================================================= */

  function renderCounts() {

    const stories =
      state.stories;


    if (!state.location) {

      if ($("#nearCount")) {
        $("#nearCount")
          .textContent = "—";
      }

      if ($("#districtCount")) {
        $("#districtCount")
          .textContent = "—";
      }

      if ($("#stateCount")) {
        $("#stateCount")
          .textContent = "—";
      }

      return;

    }


    const near =
      stories.filter(
        story =>
          locationScore(story) >= 70
      ).length;


    const district =
      stories.filter(
        story =>
          locationScore(story) >= 55
      ).length;


    const stateNews =
      stories.filter(
        story =>
          locationScore(story) >= 30
      ).length;


    if ($("#nearCount")) {

      $("#nearCount")
        .textContent =
        near;

    }


    if ($("#districtCount")) {

      $("#districtCount")
        .textContent =
        district;

    }


    if ($("#stateCount")) {

      $("#stateCount")
        .textContent =
        stateNews;

    }

  }


  function showLocalStories() {

    if (!state.location) {

      setStatus(
        "Finding local stories around you…"
      );

      detectLocation();

      return;

    }


    const localStories =
      state.stories
        .filter(
          story =>
            locationScore(story) >= 30
        )
        .sort(
          (a, b) =>
            (
              locationScore(b) +
              freshnessScore(b)
            ) -
            (
              locationScore(a) +
              freshnessScore(a)
            )
        );


    renderMoreStories(
      localStories
    );


    setStatus(
      localStories.length
        ? `${localStories.length} local stories around you`
        : "No local stories available yet."
    );


    $("#stories")
      ?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });

  }


  /* =========================================================
     CONTROLS
  ========================================================= */

  function syncControls() {

    $$("[data-category]")
      .forEach(
        element =>
          element.classList.toggle(
            "active",
            element.dataset.category ===
            state.category
          )
      );


    $$("[data-speed]")
      .forEach(
        element =>
          element.classList.toggle(
            "active",
            Number(
              element.dataset.speed
            ) === state.speed
          )
      );

  }


  function setCategory(
    category,
    scroll = true
  ) {

    state.category =
      category;


    render();


    if (scroll) {

      $("#stories")
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

    }

  }


  /* =========================================================
     SEARCH
  ========================================================= */

  function openSearch() {

    const overlay =
      $("#searchOverlay");


    if (!overlay) {
      return;
    }


    overlay.hidden =
      false;


    $("#searchInput")
      ?.focus();

  }


  function closeSearch() {

    const overlay =
      $("#searchOverlay");


    if (overlay) {
      overlay.hidden =
        true;
    }

  }


  function runSearch(query) {

    const box =
      $("#searchResults");


    if (!box) {
      return;
    }


    const q =
      String(query || "")
        .trim()
        .toLowerCase();


    if (!q) {

      box.innerHTML =
        "";

      return;

    }


    const results =
      state.stories
        .filter(
          story => {

            const text = [

              titleOf(story),

              summaryOf(story),

              ...pointsOf(story),

              categoryOf(story)

            ]
              .join(" ")
              .toLowerCase();


            return text.includes(q);

          }
        )
        .slice(0, 10);


    if (!results.length) {

      box.innerHTML = `

        <div class="search-result">

          No matching story yet.

        </div>

      `;

      return;

    }


    box.innerHTML =
      results
        .map(
          story => {

            const source =
              safeUrl(
                sourceOf(story)
              );


            const content = `

              <strong>
                ${esc(
                  titleOf(story)
                )}
              </strong>

              <br>

              <small>
                ${esc(
                  categoryOf(story)
                )}
              </small>

            `;


            if (source) {

              return `

                <a
                  class="search-result"
                  href="${esc(source)}"
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                >

                  ${content}

                </a>

              `;

            }


            return `

              <div class="search-result">

                ${content}

              </div>

            `;

          }
        )
        .join("");

  }


  /* =========================================================
     MANUAL LOCATION
  ========================================================= */

  function openLocationModal() {

    const modal =
      $("#locationModal");


    if (!modal) {
      return;
    }


    const location =
      state.location || {};


    if ($("#manualState")) {

      $("#manualState").value =
        location.state || "";

    }


    if ($("#manualDistrict")) {

      $("#manualDistrict").value =
        location.district || "";

    }


    if ($("#manualCity")) {

      $("#manualCity").value =
        location.city || "";

    }


    if ($("#manualTaluk")) {

      $("#manualTaluk").value =
        location.taluk || "";

    }


    if ($("#manualLocality")) {

      $("#manualLocality").value =
        location.locality || "";

    }


    modal.hidden =
      false;


    modal.setAttribute(
      "aria-hidden",
      "false"
    );

  }


  function closeLocationModal() {

    const modal =
      $("#locationModal");


    if (!modal) {
      return;
    }


    modal.hidden =
      true;


    modal.setAttribute(
      "aria-hidden",
      "true"
    );

  }


  function saveManualLocation() {

    const city =
      $("#manualCity")
        ?.value
        .trim() || "";


    const district =
      $("#manualDistrict")
        ?.value
        .trim() || "";


    const selectedState =
      $("#manualState")
        ?.value
        .trim() || "";


    const taluk =
      $("#manualTaluk")
        ?.value
        .trim() || "";


    const locality =
      $("#manualLocality")
        ?.value
        .trim() || "";


    if (
      !city &&
      !district &&
      !selectedState &&
      !locality
    ) {

      return;

    }


    saveLocation({

      country:
        "India",

      state:
        selectedState,

      district:
        district,

      city:
        city,

      taluk:
        taluk,

      locality:
        locality,

      lat:
        null,

      lon:
        null,

      source:
        "manual"

    });


    closeLocationModal();

    updateWeather();

    render();

  }


  /* =========================================================
     MENU
  ========================================================= */

  function toggleMenu() {

    const menu =
      $("#mobileMenu");


    const button =
      $("#menuBtn");


    if (!menu) {
      return;
    }


    menu.hidden =
      !menu.hidden;


    if (button) {

      button.setAttribute(
        "aria-expanded",
        String(!menu.hidden)
      );

    }

  }


  /* =========================================================
     EVENT LISTENERS
  ========================================================= */

  $$("[data-category]")
    .forEach(
      element =>
        element.addEventListener(
          "click",
          () => {

            const category =
              element.dataset.category;


            if (category) {

              setCategory(
                category
              );

            }

          }
        )
    );


  $$("[data-speed]")
    .forEach(
      element =>
        element.addEventListener(
          "click",
          () => {

            state.speed =
              Number(
                element.dataset.speed
              );


            syncControls();

          }
        )
    );


  $("#searchBtn")
    ?.addEventListener(
      "click",
      openSearch
    );


  $("#searchClose")
    ?.addEventListener(
      "click",
      closeSearch
    );


  $("#searchInput")
    ?.addEventListener(
      "input",
      event =>
        runSearch(
          event.target.value
        )
    );


  $("#menuBtn")
    ?.addEventListener(
      "click",
      toggleMenu
    );


  $("#changeLocationBtn")
    ?.addEventListener(
      "click",
      openLocationModal
    );


  /*
   * AROUND YOU